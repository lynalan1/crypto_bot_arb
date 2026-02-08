from sqlalchemy import text, create_engine
from datetime import datetime, timezone, timedelta
from config import SYMBOLS, DB_URL, NOTIONAL_USDT, FEE_SPOT, FEE_FUT, interval_hours_funding, PRICE_UPDATE_EVERY_SEC, MARKET
import time 
from decimal import Decimal


def load_data_symbols(engine, symbol: str, market: str):
    sql = text("""
    SELECT symbol, market, base_asset, quote_asset, is_active
    FROM symbols
    WHERE is_active = true
    AND symbol = :symbol
    AND market = :market
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol, 'market' : market}).mappings().first()

def load_data_funding_events(symbol, engine):

    sql = text("""
    SELECT symbol, funding_time, funding_rate, interval_hours, collected_at
    FROM funding_events
    WHERE symbol = :symbol
    ORDER BY funding_time DESC
    LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()
    
def load_data_prem_ind(symbol, engine):

    sql = text("""
    SELECT symbol, ts, mark_price, index_price, last_funding_rate, next_funding_time
    FROM premium_index_snapshots
    WHERE symbol = :symbol
    ORDER BY ts DESC
    LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()

def load_order_bbo(symbol, engine):

    sql = text("""
    SELECT ts, spot_symbol, fut_symbol,
           spot_bid_price, spot_ask_price,
           fut_bid_price, fut_ask_price,
           spot_mid, fut_mid,
           basis_abs, basis_pct
    FROM orderbook_bbo_snapshots
    WHERE spot_symbol = :symbol AND fut_symbol = :symbol
    ORDER BY ts DESC
    LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()

def build_open_position(symbol, engine, market):

    data_symbols = load_data_symbols(engine, symbol, market)
    data_fund = load_data_funding_events(symbol, engine)
    data_prem_ind = load_data_prem_ind(symbol, engine)
    data_order_bbo = load_order_bbo(symbol, engine)
    if not (data_symbols and data_fund and data_prem_ind and data_order_bbo): return

    base_asset = data_symbols['base_asset']
    quote_asset = data_symbols['quote_asset']

    notional_usdt = Decimal(NOTIONAL_USDT)
    spot_ask_price = Decimal(data_order_bbo['spot_ask_price'])
    qty_base = notional_usdt / spot_ask_price

    spot_qty = qty_base
    fut_qty = qty_base

    spot_entry_price = Decimal(data_order_bbo['spot_ask_price'])
    fut_entry_price = Decimal(data_order_bbo['fut_bid_price'])

    notional_spot = qty_base * spot_entry_price
    notional_fut  = qty_base * fut_entry_price

    fee_spot =  notional_spot * Decimal(FEE_SPOT)
    fee_fut =  notional_fut * Decimal(FEE_FUT)

    price_pnl_usdt = 0

    fees_paid_usdt = fee_spot + fee_fut  

    opened_at = datetime.now(timezone.utc)
    last_funding_ts = data_fund['funding_time']

    status = "OPEN"

    res = {
        "symbol" : symbol,
        "opened_at": opened_at,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "status": status,
        "spot_side": "LONG",
        "fut_side": "SHORT",
        "notional_usdt": notional_usdt,
        "spot_qty": spot_qty,
        "fut_qty": fut_qty,
        "spot_entry_price": spot_entry_price,
        "fut_entry_price": fut_entry_price,
        "fees_paid_usdt": fees_paid_usdt,
        "price_pnl_usdt": price_pnl_usdt,
        'last_funding_ts' : last_funding_ts,
        'qty_base' : qty_base
    }

    return res

def open_position(engine, data: dict) -> int:
    sql = text("""
    INSERT INTO paper_positions (
        symbol, status,
        spot_qty, fut_qty,
        spot_entry_price, fut_entry_price,
        notional_usdt,
        fees_paid_usdt,
        price_pnl_usdt,
        opened_at,
        base_asset, quote_asset, 
        last_funding_ts, qty_base,
        spot_side, fut_side
    )
    VALUES (
        :symbol, :status,
        :spot_qty, :fut_qty,
        :spot_entry_price, :fut_entry_price,
        :notional_usdt,
        :fees_paid_usdt,
        :price_pnl_usdt,
        :opened_at,
        :base_asset, :quote_asset, 
        :last_funding_ts, :qty_base,
        :spot_side, :fut_side
    )
    RETURNING id
    """)

    with engine.begin() as conn:
        result = conn.execute(sql, data)
        position_id = result.scalar_one()   # ← ВАЖНО

    return position_id

def refresh_open_positions(engine):
    now_utc = datetime.now(timezone.utc)

    with engine.begin() as conn:
        positions = conn.execute(text("""
            SELECT
                id,
                symbol,
                qty_base,
                fut_side,
                spot_entry_price,
                fut_entry_price,
                price_pnl_usdt,
                funding_pnl_usdt,
                fees_paid_usdt,
                last_funding_ts,
                last_price_update_ts
            FROM paper_positions
            WHERE status = 'OPEN'
            FOR UPDATE
        """)).mappings().all()

        for pos in positions:
            pid = pos["id"]
            symbol = pos["symbol"]

            
            inc = 0.0
            ft_apply = None

            prem = load_data_prem_ind(symbol, engine)
            funding_evens = load_data_funding_events(symbol, engine)

            if prem and prem["next_funding_time"]:

                next_ft = prem["next_funding_time"]
                ft_apply = next_ft - timedelta(hours=int(interval_hours_funding))

                last_paid = pos["last_funding_ts"]
                if now_utc >= next_ft and (last_paid is None or last_paid < ft_apply):

                    side = 1 if pos["fut_side"] == "LONG" else -1
                    notional = Decimal(pos["qty_base"]) * Decimal(prem["mark_price"])
                    rate = Decimal(funding_evens["funding_rate"])
                    inc = -side * notional * rate

                    conn.execute(text("""
                        UPDATE paper_positions
                        SET funding_pnl_usdt = funding_pnl_usdt + :inc,
                            last_funding_ts = :ft,
                            updated_at = now()
                        WHERE id = :pid
                    """), {
                        "pid": pid,
                        "inc": inc,
                        "ft": ft_apply
                    })

            funding_new = Decimal(pos["funding_pnl_usdt"] or 0) + Decimal(inc)

           
            price_pnl = Decimal(pos["price_pnl_usdt"] or 0)
            can_update_price = (
                pos["last_price_update_ts"] is None or
                (now_utc - pos["last_price_update_ts"]).total_seconds() >= int(PRICE_UPDATE_EVERY_SEC)
            )

            if can_update_price:
                bbo = load_order_bbo(symbol, engine)
                if bbo:
                    qty = Decimal(pos["qty_base"])
                    spot_exit = Decimal(bbo["spot_bid_price"])
                    fut_exit  = Decimal(bbo["fut_ask_price"])

                    price_pnl = (
                        qty * (spot_exit - Decimal(pos["spot_entry_price"])) +
                        qty * (Decimal(pos["fut_entry_price"]) - fut_exit)
                    )

                    conn.execute(text("""
                        UPDATE paper_positions
                        SET price_pnl_usdt = :price_pnl,
                            last_price_update_ts = :now_ts,
                            updated_at = now()
                        WHERE id = :pid
                    """), {
                        "pid": pid,
                        "price_pnl": price_pnl,
                        "now_ts": now_utc
                    })

           
            fees = Decimal(pos["fees_paid_usdt"] or 0)
            total = price_pnl + funding_new - fees

            conn.execute(text("""
                UPDATE paper_positions
                SET total_pnl_usdt = :total,
                    updated_at = now()
                WHERE id = :pid
            """), {
                "pid": pid,
                "total": total
            })

if __name__ == "__main__":
    
    engine = create_engine(DB_URL)
    
    for s in SYMBOLS:
        for m in MARKET:

            s = s.upper()
            data_res = build_open_position(s, engine, m)

            if data_res:
                pid = open_position(engine, data_res)

    while True:
        print('зп')
        refresh_open_positions(engine)
        time.sleep(1)
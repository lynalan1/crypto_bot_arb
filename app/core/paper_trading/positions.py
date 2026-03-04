from sqlalchemy import text, create_engine
from datetime import datetime, timezone, timedelta
from config import SYMBOLS, DB_URL, NOTIONAL_USDT, FEE_SPOT, FEE_FUT, PRICE_UPDATE_EVERY_SEC, MARKET
from decimal import Decimal
import logging
import time

logger = logging.getLogger(__name__)

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

def load_paper_cashflow(symbol, engine):
    
    sql = text("""
    SELECT position_id, symbol, funding_time, funding_rate,
           mark_price, notional_usdt, cashflow_usdt
    FROM paper_funding_cashflows
    WHERE symbol = :symbol
    ORDER BY ts DESC
    LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()

def apply_funding_cashflows(engine, dry_run: bool = True, limit_positions: int = 50):
    now_utc = datetime.now(timezone.utc)

    
    sql_positions = text("""
        SELECT
            id, symbol, qty_base, fut_side, last_funding_ts
        FROM paper_positions
        WHERE status = 'OPEN'
        ORDER BY opened_at ASC
        LIMIT :limit
        FOR UPDATE
    """)

    
    sql_next_funding = text("""
        SELECT funding_time, funding_rate
        FROM funding_events
        WHERE symbol = :symbol AND (funding_time > :last_ts)
        ORDER BY funding_time
        LIMIT 1
    """)

    
    sql_mark = text("""
        SELECT mark_price
        FROM premium_index_snapshots
        WHERE symbol = :symbol
        ORDER BY ts DESC
        LIMIT 1
    """)

    
    sql_ins_cashflow = text("""
        INSERT INTO paper_funding_cashflows (
            position_id, symbol, funding_time, funding_rate,
            mark_price, notional_usdt, cashflow_usdt
        )
        VALUES (
            :position_id, :symbol, :funding_time, :funding_rate,
            :mark_price, :notional_usdt, :cashflow_usdt
        )
        ON CONFLICT (position_id, funding_time) DO NOTHING
        RETURNING id
    """)

    
    sql_upd_pos = text("""
        UPDATE paper_positions
        SET funding_pnl_usdt = funding_pnl_usdt + :cashflow_usdt,
            last_funding_ts  = :funding_time,
            updated_at       = now()
        WHERE id = :position_id
    """)

    results = []  

    with engine.begin() as conn:

        conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        positions = conn.execute(sql_positions, {"limit": limit_positions}).mappings().all()

        for pos in positions:
            pid = pos["id"]
            symbol = pos["symbol"]
            last_ts = pos["last_funding_ts"]
            next_f = conn.execute(sql_next_funding, {
                "symbol": symbol,
                "last_ts": last_ts
            }).mappings().first()
            if not next_f:
                continue

            funding_time = next_f["funding_time"]
            funding_rate = Decimal(next_f["funding_rate"])

            
            if funding_time > now_utc:
                continue

            mark = conn.execute(sql_mark, {"symbol": symbol}).mappings().first()
            if not mark:
                continue

            mark_price = Decimal(mark["mark_price"])
            qty_base = Decimal(pos["qty_base"])
            fut_side = pos["fut_side"] or "SHORT"

           
            side = Decimal(1) if fut_side == "LONG" else Decimal(-1)

            notional_usdt = qty_base * mark_price
            cashflow_usdt = (-side) * notional_usdt * funding_rate

            param = {
                "position_id": pid,
                "symbol": symbol,
                "funding_time": funding_time,
                "funding_rate": funding_rate,
                "mark_price": mark_price,
                "notional_usdt": notional_usdt,
                "cashflow_usdt": cashflow_usdt,
            }

            if dry_run:
                results.append(param)
                continue

            
            inserted = conn.execute(sql_ins_cashflow, param).scalar()

           
            if inserted is None:
                continue

            
            conn.execute(sql_upd_pos, param)

    return results

def build_open_position(symbol, engine, market):

    data_symbols = load_data_symbols(engine, symbol, market)
    data_fund = load_data_funding_events(symbol, engine)
    data_prem_ind = load_data_prem_ind(symbol, engine)
    data_order_bbo = load_order_bbo(symbol, engine)

    if not all([data_symbols, data_fund, data_prem_ind, data_order_bbo]):

        logger.warning(f"[build_open_position] missing data for {symbol}")
        return None

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

    price_pnl_usdt = Decimal(0)

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
        position_id = result.scalar_one()  

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
        """)).mappings().all()

    for pos in positions:

        pid = pos["id"]
        symbol = pos["symbol"]
        funding_new = Decimal(pos["funding_pnl_usdt"] or 0)
       
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

       
        fees = Decimal(pos["fees_paid_usdt"] or 0)
        total = price_pnl + funding_new - fees
        
        with engine.begin() as conn:
            
            conn.execute(text("""
                UPDATE paper_positions
                SET total_pnl_usdt       = :total,
                    price_pnl_usdt       = :price_pnl,
                    last_price_update_ts = :now_ts,
                    updated_at           = now()
                WHERE id = :pid
            """), {
                "pid": pid,
                "total": total,
                "price_pnl": price_pnl,
                "now_ts": now_utc
            })
            

if __name__ == "__main__":
    
    engine = create_engine(DB_URL)
    sql = text("""
                    SELECT id FROM paper_positions
                    WHERE symbol = :symbol AND status = 'OPEN'
                """)
    

    for s in SYMBOLS:
        symbol = s.upper()
        for m in MARKET:
            
            with engine.begin() as conn:
                existing = conn.execute(sql, {"symbol": symbol}).first()

            if not existing:
                data_res = build_open_position(symbol, engine, m)

                if data_res:
                    pid = open_position(engine, data_res)

    last_funding_apply = datetime.now(timezone.utc)

    while True:

        refresh_open_positions(engine)
        now = datetime.now(timezone.utc)

        if (now - last_funding_apply).total_seconds() >= 60:
            apply_funding_cashflows(engine, dry_run=False)
            last_funding_apply = now
            logger.info(f"[positions] funding cashflows applied at {last_funding_apply}")

        time.sleep(1)

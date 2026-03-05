from sqlalchemy import text, create_engine
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def apply_funding_cashflows(engine, SYMBOLS):
    
    def load_pos(engine, symbol):

        sql_pos = text("""SELECT id, symbol, qty_base, fut_side, last_funding_ts
            FROM paper_positions
            WHERE symbol = :symbol AND status = 'OPEN'
            ORDER BY last_funding_ts DESC
            LIMIT 1""")

        with engine.connect() as conn:

            return conn.execute(sql_pos, {'symbol' : symbol}).mappings().first()

    def load_next_funding(engine, symbol, last_funding_ts):
        sql = text("""
            SELECT funding_time, funding_rate
            FROM funding_events
            WHERE symbol = :symbol
            AND funding_time > :last_funding_ts
            ORDER BY funding_time
            LIMIT 1
        """)

        with engine.connect() as conn:
            return conn.execute(sql, {
                "symbol": symbol,
                "last_funding_ts": last_funding_ts
            }).mappings().first()

    def load_data_prem_ind(engine, symbol, funding_time):

        sql = text("""
        SELECT mark_price
        FROM premium_index_snapshots
        WHERE symbol=:symbol AND ts <= :funding_time
        ORDER BY ts DESC
        LIMIT 1
        """)

        with engine.connect() as conn:
            return conn.execute(sql, {"symbol": symbol, 'funding_time' : funding_time}).mappings().first()
        
    def load_paper_cashflow(engine, symbol):

            data_pos = load_pos(engine, symbol)
            
            if not data_pos: return None
            data_funding = load_next_funding(engine, symbol, data_pos['last_funding_ts'])

            if not data_funding: return None

            if data_funding["funding_time"] > datetime.now(timezone.utc): return None
            
            data_prem = load_data_prem_ind(engine, symbol, data_funding["funding_time"])
            
            if not data_prem:

                logger.warning(f"[positions_cashflow] no mark_price for {symbol} at {data_funding['funding_time']}")
                return None
            
            # расчет параметров
            notional_usdt = Decimal(str(data_pos['qty_base'])) * Decimal(str(data_prem['mark_price']))
            funding_rate = Decimal(data_funding['funding_rate'])
            side = Decimal(1) if data_pos["fut_side"] == "LONG" else Decimal(-1)
            cashflow_usdt = Decimal(-side * notional_usdt * funding_rate)
            


            param = {'position_id' : data_pos['id'],
                    'symbol' : symbol,
                    'funding_time' : data_funding['funding_time'],
                    'funding_rate' : funding_rate,
                    'mark_price' : data_prem['mark_price'],
                    'notional_usdt' : notional_usdt,
                    'cashflow_usdt': cashflow_usdt,
                    }
            
            return param

    

    sql_cashflow = text("""
            INSERT INTO paper_funding_cashflows (
                position_id, symbol, funding_time,
                funding_rate, mark_price,
                notional_usdt, cashflow_usdt
            )
            VALUES (
                :position_id, :symbol, :funding_time,
                :funding_rate, :mark_price,
                :notional_usdt, :cashflow_usdt
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
    
    for s in SYMBOLS:

        sym = s.upper()

        try:

            data_cashflow = load_paper_cashflow(engine, sym)
        except Exception as e:

            logger.error(f'[positions_cashflow] failed for {sym}: {e}')
            continue

        if not data_cashflow:
            continue

        with engine.begin() as conn:
            
            new_id = conn.execute(sql_cashflow, data_cashflow).scalar()
            
            if new_id is not None:
                conn.execute(sql_upd_pos, data_cashflow)
                logger.info(f"[positions_cashflow] {sym}: cashflow {data_cashflow['cashflow_usdt']:.6f} USDT recorded")

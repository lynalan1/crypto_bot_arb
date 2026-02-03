from sqlalchemy import text, create_engine
from config import SYMBOLS, DB_URL

def load_data_symbols(engine):
    
    sql = text("""
    SELECT symbol, market, base_asset, quote_asset, is_active
    FROM symbols
    WHERE is_active = true
    ORDER BY symbol, market
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()
    

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

def update_data_pos(symbol, engine):

    data_symbols = load_data_symbols(engine)
    data_fund = load_data_funding_events(symbol, engine)
    data_prem_ind = load_data_prem_ind(symbol, engine)
    data_order_bbo = load_order_bbo(symbol, engine)

    print(data_order_bbo)


if __name__ == "__main__":

    engine = create_engine(DB_URL)
    for s in SYMBOLS:

        update_data_pos(s.upper(), engine)
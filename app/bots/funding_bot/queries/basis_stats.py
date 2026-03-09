from sqlalchemy import text

def get_currect_basis(engine, symbol):

    # получение данных для конретного символа
    sql = text("""
            SELECT ts, spot_symbol, fut_symbol,
           spot_bid_price, spot_ask_price,
           fut_bid_price, fut_ask_price,
           spot_mid, fut_mid,
           basis_abs, basis_pct
            FROM orderbook_bbo_snapshots
            WHERE spot_symbol = :symbol AND fut_symbol = :symbol
            ORDER BY ts DESC
            LIMIT 1""")
    
    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()

def get_basis_anomalies(engine, threshold_pct=0.005, limit=10):

    sql = text("""
            SELECT ts, spot_symbol, fut_symbol,
           spot_bid_price, spot_ask_price,
           fut_bid_price, fut_ask_price,
           spot_mid, fut_mid,
           basis_abs, basis_pct
            FROM orderbook_bbo_snapshots
            WHERE basis_pct >= :threshold_pct
            ORDER BY ts DESC
            LIMIT :limit""")
    

    with engine.connect() as conn:
        return conn.execute(sql, {"threshold_pct": threshold_pct, 'limit': limit}).mappings().all()
    
    
def get_basis_history(engine, symbol, hours=24):

    sql = text("""
            SELECT ts, spot_symbol, fut_symbol,
           spot_bid_price, spot_ask_price,
           fut_bid_price, fut_ask_price,
           spot_mid, fut_mid,
           basis_abs, basis_pct
            FROM orderbook_bbo_snapshots
            WHERE ts >= now() - interval ':hours hours' AND spot_symbol = :symbol AND fut_symbol = :symbol
            ORDER BY ts DESC
            """)
    
    with engine.connect() as conn:

        return conn.execute(sql, {"hours": hours, 'symbol': symbol, 'hours': hours}).mappings().all()
    
def get_basis_summary(engine, symbol, days=7, limit = 20):

    sql = text("""
         SELECT
            AVG(basis_pct_avg)      as mean_basis_pct,
            AVG(spot_spread_avg)    as mean_spot_spread,
            AVG(fut_spread_avg)     as mean_fut_spread,
            STDDEV(basis_pct_avg)   as std_basis_pct,
            MIN(basis_abs_min)      as min_basis,
            MAX(basis_abs_max)      as max_basis,
            COUNT(*)                as samples
               
          FROM basis_ohlc_1m
          WHERE minute_ts >= now() - interval ':days days' AND fut_symbol = :symbol
          LIMIT :limit""")
    
    with engine.connect() as conn:

        return conn.execute(sql, {"days": days, 'symbol': symbol, 'limit': limit}).mappings().first()

from sqlalchemy import text


def get_top_funding_symbols(engine, limit=10):
    # Топ символов по среднему funding rate за последние N дней

    sql = text("""
        SELECT symbol,
               AVG(funding_mean)    as avg_funding,
               AVG(positive_ratio)  as avg_positive_ratio,
               COUNT(*)             as days_count
        FROM funding_stats_daily
        WHERE day >= now() - interval '30 days'
        GROUP BY symbol
        ORDER BY avg_funding DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:

        return conn.execute(sql, {'limit' : limit}).mappings().all()
    
def get_funding_anomalies(engine, threshold=0.001):

    # аномалии в данных
    sql = text("""
        SELECT symbol, funding_rate, funding_time
        FROM funding_events
        WHERE funding_time = (
            SELECT MAX(funding_time) 
            FROM funding_events fe2 
            WHERE fe2.symbol = funding_events.symbol
        )
        AND funding_rate > :threshold
        ORDER BY funding_rate DESC
    """)
    
    with engine.connect() as conn:

        return conn.execute(sql, {'threshold': threshold})
    

def get_funding_history_for_symbol(engine, symbol, days=30):

    # история для конкретного символа за конкретные дни
    sql = text("""
        SELECT day,
               funding_mean,
               funding_std,
               positive_ratio
        FROM funding_stats_daily
        WHERE symbol = :symbol
        AND day >= now() - interval ':days'
        ORDER BY day ASC
    """)
    with engine.connect() as conn:

        return conn.execute(sql, {'symbol' : symbol, 'days': days}).mappings().all()


def get_persistent_positive_symbols(engine, min_positive_ratio=0.7, days=30):

    # символы у которых рейтинг больше заданного(min_positive_ratio)
    sql = text("""
        SELECT symbol,
               AVG(positive_ratio) as avg_positive_ratio,
               AVG(funding_mean)   as avg_rate
        FROM funding_stats_daily
        WHERE day >= now() - interval ':days days'
        GROUP BY symbol
        HAVING AVG(positive_ratio) >= :min_ratio
        ORDER BY avg_rate DESC
    """)

    with engine.connect() as conn:

        return conn.execute(sql, {'min_ratio': min_positive_ratio, 'days': days}).mappings().all()
    
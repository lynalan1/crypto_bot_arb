from sqlalchemy import text


def get_current_basis(engine, symbol: str):
    """Последний снапшот basis для символа."""

    sql = text("""
        SELECT
            ts, spot_symbol, fut_symbol,
            spot_mid, fut_mid,
            basis_abs, basis_pct
        FROM orderbook_bbo_snapshots
        WHERE spot_symbol = :symbol
        ORDER BY ts DESC
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {"symbol": symbol}).mappings().first()


def get_basis_anomalies(engine, threshold_pct: float = 0.005, limit: int = 10):
    """Снапшоты с basis выше порога."""

    sql = text("""
        SELECT
            ts, spot_symbol, fut_symbol,
            spot_mid, fut_mid,
            basis_abs, basis_pct
        FROM orderbook_bbo_snapshots
        WHERE ABS(basis_pct) >= :threshold_pct
        ORDER BY ts DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql, {"threshold_pct": threshold_pct, "limit": limit}
        ).mappings().all()


def get_basis_history(engine, symbol: str, hours: int = 24):
    """История basis за N часов для символа."""

    sql = text("""
        SELECT
            ts,
            spot_mid,
            fut_mid,
            basis_abs,
            basis_pct
        FROM orderbook_bbo_snapshots
        WHERE spot_symbol = :symbol
        AND   ts >= now() - (:hours * interval '1 hour')
        ORDER BY ts ASC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql, {"symbol": symbol, "hours": hours}
        ).mappings().all()


def get_basis_summary(engine, symbol: str, days: int = 7):
    """Агрегат из basis_ohlc_1m за N дней."""

    sql = text("""
        SELECT
            AVG(basis_pct_avg)    AS avg_basis_pct,
            STDDEV(basis_pct_avg) AS std_basis_pct,
            MIN(basis_abs_min)    AS min_basis_abs,
            MAX(basis_abs_max)    AS max_basis_abs,
            AVG(spot_spread_avg)  AS avg_spot_spread,
            AVG(fut_spread_avg)   AS avg_fut_spread,
            COUNT(*)              AS samples
        FROM basis_ohlc_1m
        WHERE fut_symbol = :symbol
        AND   minute_ts >= now() - (:days * interval '1 day')
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql, {"symbol": symbol, "days": days}
        ).mappings().first()
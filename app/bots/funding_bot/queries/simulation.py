from sqlalchemy import text
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from config import FEE_SPOT, FEE_FUT


def calculate_simulation(
    engine,
    symbol: str,
    notional_usdt: float,
    days: int,
    side: str = "SHORT",  
):

    if side not in ("SHORT", "LONG"):
        raise ValueError(f"side must be SHORT or LONG, got: {side}")

    date_from = datetime.now(timezone.utc) - timedelta(days=days)
    date_to   = datetime.now(timezone.utc)

    notional  = Decimal(str(notional_usdt))


    side_mult = Decimal(1) if side == "SHORT" else Decimal(-1)

    sql_history = text("""
        SELECT
            funding_time,
            funding_rate,
            interval_hours
        FROM funding_events
        WHERE symbol       = :symbol
        AND   funding_time BETWEEN :date_from AND :date_to
        ORDER BY funding_time ASC
    """)

    sql_avg_price = text("""
        SELECT AVG(spot_mid) as avg_spot_price
        FROM orderbook_bbo_snapshots
        WHERE spot_symbol = :symbol
        AND   ts BETWEEN :date_from AND :date_from + interval '1 hour'
    """)

    with engine.connect() as conn:

        rows = conn.execute(sql_history, {
            "symbol":    symbol,
            "date_from": date_from,
            "date_to":   date_to,
        }).mappings().all()

        if not rows:
            return None, None

        price_row = conn.execute(sql_avg_price, {
            "symbol":    symbol,
            "date_from": date_from,
        }).mappings().first()

        avg_entry_price = (
            Decimal(str(price_row["avg_spot_price"]))
            if price_row and price_row["avg_spot_price"]
            else None
        )

    fee_open  = notional * (Decimal(str(FEE_SPOT)) + Decimal(str(FEE_FUT)))
    fee_close = notional * (Decimal(str(FEE_SPOT)) + Decimal(str(FEE_FUT)))
    total_fees = fee_open + fee_close

    history       = []
    cumulative    = Decimal(0)
    total_funding = Decimal(0)

    for row in rows:
        rate     = Decimal(str(row["funding_rate"]))
        cashflow = side_mult * notional * rate

        cumulative    += cashflow
        total_funding += cashflow

        history.append({
            "funding_time":        row["funding_time"],
            "funding_rate":        float(rate),
            "interval_hours":      row["interval_hours"],
            "cashflow_usdt":       float(cashflow),
            "cumulative_cashflow": float(cumulative),
        })

    total_pnl = total_funding - total_fees

    summary = {
        "symbol":          symbol,
        "side":            side,
        "notional_usdt":   float(notional),
        "date_from":       date_from,
        "date_to":         date_to,
        "days":            days,
        "intervals_count": len(rows),
        "avg_entry_price": float(avg_entry_price) if avg_entry_price else None,
        "funding_pnl":     float(total_funding),
        "fees":            float(total_fees),
        "total_pnl":       float(total_pnl),
        "total_pnl_pct":   float(total_pnl / notional * 100),
    }

    return summary, history


def save_simulation(engine, telegram_id: int, summary: dict) -> int:

    upsert_user = text("""
        INSERT INTO bot_users (telegram_id, created_at)
        VALUES (:telegram_id, now())
        ON CONFLICT (telegram_id) DO NOTHING
    """)

    insert_sim = text("""
        INSERT INTO user_simulations (
            telegram_id, symbol, side, notional_usdt,
            date_from, date_to, days,
            funding_pnl, fees, total_pnl, total_pnl_pct,
            intervals_count, created_at
        )
        VALUES (
            :telegram_id, :symbol, :side, :notional_usdt,
            :date_from, :date_to, :days,
            :funding_pnl, :fees, :total_pnl, :total_pnl_pct,
            :intervals_count, now()
        )
        RETURNING id
    """)

    with engine.begin() as conn:
        # Сначала создаём пользователя если не существует
        conn.execute(upsert_user, {"telegram_id": telegram_id})

        # вставляем симуляцию
        result = conn.execute(insert_sim, {
            "telegram_id":    telegram_id,
            "symbol":         summary["symbol"],
            "side":           summary["side"],
            "notional_usdt":  summary["notional_usdt"],
            "date_from":      summary["date_from"],
            "date_to":        summary["date_to"],
            "days":           summary["days"],
            "funding_pnl":    float(summary["funding_pnl"]),
            "fees":           float(summary["fees"]),
            "total_pnl":      float(summary["total_pnl"]),
            "total_pnl_pct":  float(summary["total_pnl_pct"]),
            "intervals_count": summary["intervals_count"],
        })

        return result.scalar_one()


def get_user_simulations(engine, telegram_id: int):

    sql = text("""
        SELECT
            id, symbol, notional_usdt,
            date_from, date_to, days,
            funding_pnl, fees, total_pnl, total_pnl_pct,
            intervals_count, created_at
        FROM user_simulations
        WHERE telegram_id = :telegram_id
        ORDER BY created_at DESC
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {
            "telegram_id": telegram_id,
        }).mappings().all()

def delete_simulation(engine, sim_id: int, telegram_id: int) -> bool:
    """Удаляет симуляцию. telegram_id для защиты — нельзя удалить чужую."""

    sql = text("""
        DELETE FROM user_simulations
        WHERE id = :sim_id AND telegram_id = :telegram_id
        RETURNING id
    """)

    with engine.begin() as conn:
        result = conn.execute(sql, {
            "sim_id":      sim_id,
            "telegram_id": telegram_id,
        })
        return result.first() is not None
    
def get_user_simulation_detail(engine, sim_id: int, telegram_id: int):

    sql = text("""
        SELECT *
        FROM user_simulations
        WHERE id          = :sim_id
        AND   telegram_id = :telegram_id
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {
            "sim_id":      sim_id,
            "telegram_id": telegram_id,
        }).mappings().first()


def get_profile_summary(engine, telegram_id: int):

    sql = text("""
        SELECT
            COUNT(*)           as simulations_count,
            SUM(notional_usdt) as total_notional,
            SUM(funding_pnl)   as total_funding_pnl,
            SUM(fees)          as total_fees,
            SUM(total_pnl)     as total_pnl
        FROM user_simulations
        WHERE telegram_id = :telegram_id
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {
            "telegram_id": telegram_id,
        }).mappings().first()

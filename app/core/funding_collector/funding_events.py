import time
import requests
from sqlalchemy import create_engine, text
from config import DB_URL, SYMBOLS, url_fund_rate
from datetime import datetime, timezone

def get_funding_history(symbol="ETHUSDT", limit=270):

    FUNDING_INTERVAL_HOURS = 8
    params = {"symbol": symbol, "limit": limit}
    r_fund_rate = requests.get(url_fund_rate, params=params, timeout=10)
    r_fund_rate.raise_for_status()
    data = r_fund_rate.json()
    clean_data = []

    for row in data:
        funding_time_ms = int(row["fundingTime"])

        clean_data.append({
            "symbol": row["symbol"],
            "funding_rate": float(row["fundingRate"]),
            "funding_time": datetime.fromtimestamp(funding_time_ms/1000, tz=timezone.utc),
        })


    return clean_data

def update_data(data, engine, interval):

    with engine.begin() as conn:

        for row in data:
        
            params = {
                "symbol": row["symbol"],
                "funding_time": row["funding_time"],
                "interval_hours": interval,
                "funding_rate": row["funding_rate"],
                "collected_at": datetime.now(timezone.utc),
            }

            conn.execute(text("""
                INSERT INTO funding_events (
                    symbol, funding_time, interval_hours, funding_rate, collected_at
                )
                VALUES (
                    :symbol, :funding_time, :interval_hours, :funding_rate, :collected_at
                )
                ON CONFLICT (symbol, funding_time)
                DO UPDATE SET
                    funding_rate = EXCLUDED.funding_rate,
                    collected_at = EXCLUDED.collected_at
            """), params)


if __name__ == "__main__":

    engine = create_engine(DB_URL)
    FUNDING_INTERVAL_HOURS = 8
    for s in SYMBOLS:

        data = get_funding_history(symbol=s.upper(), )
        update_data(data, engine, FUNDING_INTERVAL_HOURS)
    
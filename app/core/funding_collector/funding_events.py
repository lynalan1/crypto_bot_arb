import requests
from sqlalchemy import text, create_engine
from config import  url_fund_rate, FUNDING_INTERVAL_HOURS
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def update_funding_events(engine, SYMBOLS):

    # 270 = 90 дней при 8h интервале
    def get_funding_history(symbol="ETHUSDT", limit=270, interval=8):

        params = {"symbol": symbol, "limit": limit}
        r_fund_rate = requests.get(url_fund_rate, params=params, timeout=10)
        r_fund_rate.raise_for_status()
        recv_ts = datetime.now(timezone.utc)   
        data = r_fund_rate.json()
        clean_data = []

        for row in data:
            funding_time_ms = int(row["fundingTime"])

            clean_data.append({
                "symbol": row["symbol"],
                "funding_rate": float(row["fundingRate"]),
                "funding_time": datetime.fromtimestamp(funding_time_ms/1000, tz=timezone.utc),
                'interval_hours': interval,
                "collected_at": recv_ts,  
            })


        return clean_data

    def update_data(data):

        try:

            with engine.begin() as conn:
                
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
                    """), data)

        except Exception as e:
            logger.error(f"[funding_events_sql] failed: {e}")
                

    interval = float(FUNDING_INTERVAL_HOURS)

    for s in SYMBOLS:

        if not s or not s.strip():
            logger.warning(f"[funding_events] skipping empty symbol")
            continue

        try:
            
            data = get_funding_history(symbol=s.upper(), interval = interval)
            update_data(data)
            logger.info(f"[funding_events] {s}: upserted {len(data)} rows")
            
        except Exception as e:
            logger.error(f"[funding_events] failed for {s}: {e}")
            continue

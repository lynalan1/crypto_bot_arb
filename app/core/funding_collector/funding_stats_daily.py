from sqlalchemy import create_engine, text
import requests
from collections import deque
from typing import Dict
from datetime import datetime, timezone
import numpy as np
from config import DB_URL, SYMBOLS, url_fund_rate

def bucket_1d(dt):

    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def write_daily_stats(conn, param):

    return conn.execute(   
                            text("""
                                INSERT INTO funding_stats_daily (
                                    symbol,
                                    day,
                                    intervals_count,
                                    funding_mean,
                                    funding_std,
                                    funding_min,
                                    funding_max,
                                    positive_ratio,
                                    updated_at
                                )
                                VALUES (
                                    :symbol,
                                    :day,
                                    :intervals_count,
                                    :funding_mean,
                                    :funding_std,
                                    :funding_min,
                                    :funding_max,
                                    :positive_ratio,
                                    now()
                                )
                                ON CONFLICT (symbol, day)
                                DO UPDATE SET
                                    intervals_count = EXCLUDED.intervals_count,
                                    funding_mean    = EXCLUDED.funding_mean,
                                    funding_std     = EXCLUDED.funding_std,
                                    funding_min     = EXCLUDED.funding_min,
                                    funding_max     = EXCLUDED.funding_max,
                                    positive_ratio  = EXCLUDED.positive_ratio,
                                    updated_at      = now();
                            """),
                            param
                        )
                        
def get_funding_stats(symbol="ETHUSDT", db_url="", limit=270):

    url = url_fund_rate
    params = {"symbol": symbol, 'limit' : limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    d = r.json()
    d_sorted = sorted(d, key=lambda x: int(x["fundingTime"]))

    clean_data: Dict[str, Dict[str, deque]] = {}
    current_day: Dict[str, datetime] = {}   

    for row in d_sorted:

        rate =  float(row["fundingRate"])
        
        if symbol not in clean_data:
            clean_data[symbol] = {
                "funding_rate": deque(),
            }

        day_ts = bucket_1d(datetime.fromtimestamp(int(row["fundingTime"]) / 1000, tz=timezone.utc))

        if symbol not in current_day:

            current_day[symbol] = day_ts


        if current_day[symbol] != day_ts:

            prev_ts = current_day[symbol]

            n = len(clean_data[symbol]["funding_rate"])

            if n > 0:   

                pos_n = sum(1 for i in clean_data[symbol]["funding_rate"] if i > 0)
                
                param = {
                        "symbol": symbol,
                        "day": prev_ts.date(),                         
                        "intervals_count": int(n),                     
                        "funding_mean": float(np.mean(clean_data[symbol]["funding_rate"])),
                        "funding_std": float(np.std(clean_data[symbol]["funding_rate"], ddof=0)),
                        "funding_min": float(min(clean_data[symbol]["funding_rate"])),
                        "funding_max": float(max(clean_data[symbol]["funding_rate"])),
                        "positive_ratio": float(pos_n / n) if n else 0.0,
                       
                    }
                
                with db_url.begin() as conn:
                    
                    write_daily_stats(conn, param)

                current_day[symbol] = day_ts
                clean_data[symbol]["funding_rate"].clear()
            


        clean_data[symbol]["funding_rate"].append(rate)

    if symbol in clean_data and symbol in current_day:

        n = len(clean_data[symbol]["funding_rate"])

        if n > 0:

            prev_ts = current_day[symbol]     
            pos_n = sum(1 for x in clean_data[symbol]["funding_rate"] if x > 0)
    
            param = {
                "symbol": symbol,
                "day": prev_ts.date(),
                "intervals_count": int(n),
                "funding_mean": float(np.mean(clean_data[symbol]["funding_rate"])),
                "funding_std": float(np.std(clean_data[symbol]["funding_rate"],  ddof=0)),
                "funding_min": float(min(clean_data[symbol]["funding_rate"])),
                "funding_max": float(max(clean_data[symbol]["funding_rate"])),
                "positive_ratio": float(pos_n / n),
            }

            with db_url.begin() as conn:
                
                write_daily_stats(conn, param)

            clean_data[symbol]["funding_rate"].clear()
        
if __name__ == "__main__":

    engine = create_engine(DB_URL)

    for s in SYMBOLS:
        get_funding_stats(db_url=engine, symbol=s.upper())

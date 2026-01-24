import time
import requests
from sqlalchemy import create_engine, text


def get_funding_history(symbol="ETHUSDT", limit=10):

    
    # Endpoint: https://fapi.binance.com/fapi/v1/fundingRate

    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    clean_data = []

    for row in data:
        funding_time_ms = int(row["fundingTime"])

        clean_data.append({
            "symbol": row["symbol"],
            "funding_rate": float(row["fundingRate"]),
            "funding_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(funding_time_ms / 1000)),
        })


    return clean_data

def get_mark_price(symbol = "ETHUSDT"):

    # Endpoint: https://fapi.binance.com/fapi/v1/premiumIndex

    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    params = {"symbol": symbol}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    d = r.json()

    mark_price = d["markPrice"]

    return mark_price

def update_data(data, engine, mark_price):
    with engine.begin() as conn:
        for row in data:
            params = {
                "symbol": row["symbol"],
                "funding_time": row["funding_time"],
                "interval_hours": 8,
                "funding_rate": row["funding_rate"],
                "mark_price": mark_price,
                "collected_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            }

            conn.execute(text("""
                INSERT INTO funding_events (
                    symbol, funding_time, interval_hours, funding_rate, mark_price, collected_at
                )
                VALUES (
                    :symbol, :funding_time, :interval_hours, :funding_rate, :mark_price, :collected_at
                )
                ON CONFLICT (symbol, funding_time)
                DO UPDATE SET
                    funding_rate = EXCLUDED.funding_rate,
                    mark_price   = EXCLUDED.mark_price,
                    collected_at = EXCLUDED.collected_at
            """), params)


if __name__ == "__main__":

    engine = create_engine("postgresql+psycopg://crypto_user:crypto_pass@localhost:5438/crypto_bot_db")

    print('history')
    data = get_funding_history(limit=20)
    print('mark_price')
    mark_price = get_mark_price()
    print('upload in bd')
    
    update_data(data, engine, mark_price)
    
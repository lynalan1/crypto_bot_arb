
import time
import requests
from sqlalchemy import create_engine, text
from datetime import datetime, timezone


def get_premium_index(symbol="ETHUSDT"):
    
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    params = {"symbol": symbol}
    r = requests.get(url, params=params, timeout=10)
    recv_ts = datetime.now(timezone.utc)
    r.raise_for_status()
    d = r.json()
    clean_data = []
    nft_ms = int(d.get("nextFundingTime", 0))

    if nft_ms:
        nft_utc = datetime.now(timezone.utc)

    clean_data.append({'symbol' : d["symbol"],
                       'mark_price' : d["markPrice"],
                       'index_price' : d["indexPrice"],
                       'last_funding_rate' : d["lastFundingRate"],
                       'interest_rate' :  d.get("interestRate"),
                       'next_funding_time': nft_utc,
                       'collected_at' : datetime.now(timezone.utc),
                       'ts' : recv_ts
                       })

    return clean_data

def update_data(data, engine):

    params = data[0]

    with engine.begin() as conn:

        conn.execute(text("""
                    INSERT INTO premium_index_snapshots (
                        symbol, ts, mark_price, index_price, last_funding_rate, next_funding_time, interest_rate, collected_at
                    )
                    VALUES (
                        :symbol, :ts, :mark_price, :index_price, :last_funding_rate, :next_funding_time, :interest_rate, :collected_at
                    )
                    ON CONFLICT (symbol, ts) DO NOTHING
                """), params)
        
    
if __name__ == "__main__":

    
    engine = create_engine("postgresql+psycopg://crypto_user:crypto_pass@localhost:5438/crypto_bot_db")
    data = get_premium_index() 
    print('загрузка')
    update_data(data, engine)

import requests
from sqlalchemy import text
from datetime import datetime, timezone
from config import prem_ind

def update_premium_index(engine, SYMBOLS):

    def get_premium_index(symbol="ETHUSDT", url_prem=''):
        
        url = url_prem
        params = {"symbol": symbol}
        r = requests.get(url, params=params, timeout=10)
        recv_ts = datetime.now(timezone.utc)

        r.raise_for_status()
        d = r.json()
        clean_data = []

        nft_ms = int(d.get("nextFundingTime", 0))
        nft_utc = datetime.fromtimestamp(nft_ms / 1000, tz=timezone.utc) if nft_ms else None

        ir = d.get("interestRate")
        interest_rate = float(ir) if ir is not None else None

        clean_data.append({'symbol' : d["symbol"],
                        'mark_price' : float(d["markPrice"]),
                        'index_price' : float(d["indexPrice"]),
                        'last_funding_rate' : float(d["lastFundingRate"]),
                        'interest_rate' :  interest_rate,
                        'next_funding_time': nft_utc,
                        'collected_at' : recv_ts,
                        'ts' : recv_ts
                        })

        return clean_data

    def update_data(data, engine):

        with engine.begin() as conn:

            conn.execute(text("""
                        INSERT INTO premium_index_snapshots (
                            symbol, ts, mark_price, index_price, last_funding_rate, next_funding_time, interest_rate, collected_at
                        )
                        VALUES (
                            :symbol, :ts, :mark_price, :index_price, :last_funding_rate, :next_funding_time, :interest_rate, :collected_at
                        )
                        ON CONFLICT (symbol, ts) DO NOTHING
                    """), data)
    
    for s in SYMBOLS:

            data = get_premium_index(symbol=s.upper(), url_prem=prem_ind)
            update_data(data[0], engine)
        



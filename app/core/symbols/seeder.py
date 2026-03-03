import requests
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from config import url_fut_sym, url_spot_sym

def seed_symbols(engine, SYMBOLS):
    
    def requests_sql(eng, params):

        sql = text("""
            INSERT INTO symbols (
                symbol,
                market,
                base_asset,
                quote_asset,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                :symbol,
                :market,
                :base_asset,
                :quote_asset,
                :is_active,
                :created_at,
                :updated_at
            )
            ON CONFLICT (symbol, market)
            DO UPDATE SET
                market      = EXCLUDED.market,
                base_asset  = EXCLUDED.base_asset,
                quote_asset = EXCLUDED.quote_asset,
                is_active   = EXCLUDED.is_active,
                updated_at  = now();
        """)

        with eng.begin() as conn:
            conn.execute(sql, params)

    def get_market_sym(symbol='ETHUSDT'):

        params = {"symbol": symbol,}

        r_spot = requests.get(url_spot_sym, params=params, timeout=10)
        r_fut = requests.get(url_fut_sym, timeout=10)

        r_spot.raise_for_status()
        r_fut.raise_for_status()

        d_spot = r_spot.json()
        d_fut = r_fut.json()
        clean_data_spot = None
        clean_data_fut = None

        clean_data_spot = None
        for row in d_spot["symbols"]:
            if row["symbol"] == symbol:
                clean_data_spot = {
                    "symbol": row["symbol"],
                    "base_asset": row["baseAsset"],
                    "quote_asset": row["quoteAsset"],
                    "is_active": row.get("status") == "TRADING",
                    "created_at": datetime.now(timezone.utc),
                }
                break

        clean_data_fut = None
        for row in d_fut["symbols"]:
            if (
                row["symbol"] == symbol
                and row["contractType"] == "PERPETUAL"
                and row["quoteAsset"] == "USDT"
            ):
                clean_data_fut = {
                    "symbol": row["symbol"],
                    "base_asset": row["baseAsset"],
                    "quote_asset": row["quoteAsset"],
                    "is_active": row.get("status") == "TRADING",
                    "created_at": datetime.now(timezone.utc),
                }
                break

        return clean_data_spot, clean_data_fut


    def update_sql(data_spot, data_fut, eng):

        if data_spot:
            params_spot = {'symbol' : data_spot['symbol'],
                        'market' : 'SPOT',
                        'base_asset' : data_spot['base_asset'],
                        'quote_asset' : data_spot['quote_asset'],
                        'is_active' : data_spot["is_active"],
                        'created_at' : data_spot['created_at'],
                        'updated_at' : datetime.now(timezone.utc),
                        }
            
            requests_sql(eng, params_spot)

        if data_fut:
            params_fut = {'symbol' : data_fut['symbol'],
                        'market' : 'FUTURES_UM',
                        'base_asset' : data_fut['base_asset'],
                        'quote_asset' : data_fut['quote_asset'],
                        'is_active' : data_fut["is_active"],
                        'created_at' : data_fut['created_at'],
                        'updated_at' : datetime.now(timezone.utc),
                        }
            
            requests_sql(eng, params_fut)
        

        for s in SYMBOLS:

            data_spot, data_fut = get_market_sym(symbol=s.upper())
            update_sql(data_spot, data_fut, engine)

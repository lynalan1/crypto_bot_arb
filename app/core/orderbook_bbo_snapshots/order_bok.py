import asyncio, json, websockets
from typing import Dict, Any, Tuple
from sqlalchemy import create_engine, text
import time
from datetime import datetime, timezone

symbols = ["ethusdt"]



STREAMS = "/".join([f"{s}@bookTicker" for s in symbols])

SPOT_URL = f"wss://stream.binance.com:9443/stream?streams={STREAMS}"
FUT_URL  = f"wss://fstream.binance.com/stream?streams={STREAMS}"

async def ws_consumer(name: str, url: str, queue: asyncio.Queue):
    backoff = 1
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=10) as ws:
                backoff = 1
                
                async for raw in ws:
                    recv_ts = datetime.now(timezone.utc)
                    msg = json.loads(raw)

                    stream = msg.get("stream")
                    data = msg.get("data")
                    if not stream or not isinstance(data, dict):
                        continue

                    
                    if not all(k in data for k in ("s", "b", 'B', "a", 'A')):
                        continue

                    
                    await queue.put((name, stream, data, recv_ts))

        except (websockets.ConnectionClosed, OSError) as e:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        except Exception:
            await asyncio.sleep(2)

async def processor(queue: asyncio.Queue):
    
    engine = create_engine("postgresql+psycopg://crypto_user:crypto_pass@localhost:5438/crypto_bot_db")
    last: Dict[Tuple[str, str], Dict[str, Any]] = {}
    
    while True:
        src, stream, data, recv_ts = await queue.get()
        symbol = data["s"]
        bid = float(data["b"])
        ask = float(data["a"])
        bid_qty = float(data["B"])
        ask_qty = float(data["A"])

        last[(src, symbol)] = {"bid": bid, "ask": ask, 'bid_qty': bid_qty, "ask_qty" : ask_qty}

        
        if ("spot", symbol) in last and ("fut", symbol) in last:
            spot_mid = (last[("spot", symbol)]["bid"] + last[("spot", symbol)]["ask"]) / 2
            fut_mid  = (last[("fut", symbol)]["bid"]  + last[("fut", symbol)]["ask"]) / 2
            basis_abs = fut_mid - spot_mid
            basis_pct = (fut_mid - spot_mid) / spot_mid
            
            params = {
                'ts' : recv_ts,
                "spot_symbol": symbol,
                "spot_bid_price": last[("spot", symbol)]["bid"],
                "spot_ask_price": last[("spot", symbol)]["ask"],
                "spot_bid_qty": last[("spot", symbol)]["bid_qty"],
                "spot_ask_qty": last[("spot", symbol)]["ask_qty"],
                "fut_symbol" : symbol, 
                "fut_bid_price" : last[("fut", symbol)]["bid"], 
                "fut_ask_price" : last[("fut", symbol)]["ask"], 
                "fut_bid_qty" : last[("fut", symbol)]["bid_qty"], 
                "fut_ask_qty" : last[("fut", symbol)]["ask_qty"], 
                "spot_mid" : spot_mid, 
                "fut_mid" : fut_mid, 
                "basis_abs" : basis_abs, 
                "basis_pct" : basis_pct,
                "collected_at" : datetime.now(timezone.utc)
            }


            with engine.begin() as conn:
                
                print('запись')
                conn.execute(
                    text("""
                        INSERT INTO orderbook_bbo_snapshots (
                            ts,
                            spot_symbol, spot_bid_price, spot_ask_price, spot_bid_qty, spot_ask_qty,
                            fut_symbol,  fut_bid_price,  fut_ask_price,  fut_bid_qty,  fut_ask_qty,
                            spot_mid, fut_mid, basis_abs, basis_pct, collected_at
                        )
                        VALUES (
                            :ts,
                            :spot_symbol, :spot_bid_price, :spot_ask_price, :spot_bid_qty, :spot_ask_qty,
                            :fut_symbol,  :fut_bid_price,  :fut_ask_price,  :fut_bid_qty,  :fut_ask_qty,
                            :spot_mid, :fut_mid, :basis_abs, :basis_pct, :collected_at
                            
                        )
                        ON CONFLICT (spot_symbol, fut_symbol, ts) DO NOTHING
                    """),
                    params
                )

        queue.task_done()

async def main():
    q = asyncio.Queue(maxsize=200_000)
    await asyncio.gather(
        ws_consumer("spot", SPOT_URL, q),
        ws_consumer("fut",  FUT_URL,  q),
        processor(q),
    )



if __name__ == "__main__":

    print('Пуск')
    asyncio.run(main())


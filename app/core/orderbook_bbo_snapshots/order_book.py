import asyncio, json, websockets
from typing import Dict, Any, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
from collections import deque
from config import DB_URL, SYMBOLS, spot_url_order, fut_url_order

engine = create_engine(DB_URL)

STREAMS = "/".join([f"{s}@bookTicker" for s in SYMBOLS])

SPOT_URL = f"{spot_url_order}={STREAMS}"
FUT_URL  = f"{fut_url_order}={STREAMS}"

def floor_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)

SQL_1M = text("""
INSERT INTO basis_ohlc_1m (
    fut_symbol,
    minute_ts,
    basis_abs_avg,
    basis_abs_min,
    basis_abs_max,
    basis_pct_avg,
    spot_spread_avg,
    fut_spread_avg,
    samples_count,
    updated_at
)
VALUES (
    :fut_symbol,
    :minute_ts,
    :basis_abs_avg,
    :basis_abs_min,
    :basis_abs_max,
    :basis_pct_avg,
    :spot_spread_avg,
    :fut_spread_avg,
    :samples_count,
    now()
)
ON CONFLICT (fut_symbol, minute_ts)
DO UPDATE SET
    basis_abs_avg   = EXCLUDED.basis_abs_avg,
    basis_abs_min   = LEAST(basis_ohlc_1m.basis_abs_min, EXCLUDED.basis_abs_min),
    basis_abs_max   = GREATEST(basis_ohlc_1m.basis_abs_max, EXCLUDED.basis_abs_max),
    basis_pct_avg   = EXCLUDED.basis_pct_avg,
    spot_spread_avg = EXCLUDED.spot_spread_avg,
    fut_spread_avg  = EXCLUDED.fut_spread_avg,
    samples_count   = EXCLUDED.samples_count,
    updated_at      = now();
""")

def text_sql_1m(params: list[dict], conn):
    conn.execute(SQL_1M, params)

SQL_5S = text("""
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
""")

def text_sql_5s(params: list[dict], conn):
    conn.execute(SQL_5S, params)

def floor_5s(dt: datetime):
    
    t = int(dt.timestamp())
    bucket = (t // 5) * 5
    return datetime.fromtimestamp(bucket, tz=timezone.utc)

def floor_10s(dt: datetime):
    
    t = int(dt.timestamp())
    bucket = (t // 10) * 10
    return datetime.fromtimestamp(bucket, tz=timezone.utc)

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
    
    last: Dict[Tuple[str, str], Dict[str, Any]] = {}


    current_minute: Dict[str, datetime] = {}         
    window_1m: Dict[str, deque] = {}                  
    current_5s: Dict[str, datetime] = {}
    snapshot_to_db_1m = []
    snapshot_to_db_5s = []
    last_flush = floor_10s(datetime.now(timezone.utc))

    while True:

        src, _, data, recv_ts = await queue.get()
        try:
            symbol = data["s"]
            bid = float(data["b"])
            ask = float(data["a"])
            bid_qty = float(data["B"])
            ask_qty = float(data["A"])

            last[(src, symbol)] = {
                "bid": bid,
                "ask": ask,
                "bid_qty": bid_qty,
                "ask_qty": ask_qty,
            }

            if ("spot", symbol) not in last or ("fut", symbol) not in last:
                continue

            spot_bid = last[("spot", symbol)]["bid"]
            spot_ask = last[("spot", symbol)]["ask"]
            fut_bid  = last[("fut", symbol)]["bid"]
            fut_ask  = last[("fut", symbol)]["ask"]

            spot_mid = (spot_bid + spot_ask) / 2
            fut_mid  = (fut_bid  + fut_ask)  / 2

            if spot_mid <= 0 or fut_mid <= 0: continue 

            spot_spread_pct = (spot_ask - spot_bid) / spot_mid
            fut_spread_pct  = (fut_ask  - fut_bid)  / fut_mid

            basis_abs = fut_mid - spot_mid
            basis_pct = basis_abs / spot_mid    
            
            minute_ts = floor_minute(recv_ts)

            if symbol not in current_minute:
                
                current_minute[symbol] = minute_ts
                window_1m[symbol] = deque()

            
            if minute_ts != current_minute[symbol]:
                prev_minute = current_minute[symbol]
                w = window_1m[symbol]
                n = len(w)

                if n > 0:

                    params_1m = {
                        "fut_symbol": symbol,
                        "minute_ts": prev_minute,  
                        "basis_abs_avg": sum(x["basis"] for x in w) / n,
                        "basis_abs_min": min(x["basis"] for x in w),
                        "basis_abs_max": max(x["basis"] for x in w),
                        "basis_pct_avg": sum(x["basis_pct"] for x in w) / n,
                        "spot_spread_avg": sum(x["spot_spread"] for x in w) / n,
                        "fut_spread_avg": sum(x["fut_spread"] for x in w) / n,
                        "samples_count": n,
                    }

                    snapshot_to_db_1m.append(params_1m)

                w.clear()
                current_minute[symbol] = minute_ts

            
            window_1m[symbol].append(
                {
                    "basis": basis_abs,
                    "basis_pct": basis_pct,
                    "spot_spread": spot_spread_pct,
                    "fut_spread": fut_spread_pct,
                }
            )

            bucket_5s = floor_5s(recv_ts)

            if symbol not in current_5s:
                current_5s[symbol] = bucket_5s

            
            if bucket_5s != current_5s[symbol]:
                current_5s[symbol] = bucket_5s

                params_5s = {
                    "ts": bucket_5s,  
                    "spot_symbol": symbol,
                    "spot_bid_price": spot_bid,
                    "spot_ask_price": spot_ask,
                    "spot_bid_qty": last[("spot", symbol)]["bid_qty"],
                    "spot_ask_qty": last[("spot", symbol)]["ask_qty"],
                    "fut_symbol": symbol,
                    "fut_bid_price": fut_bid,
                    "fut_ask_price": fut_ask,
                    "fut_bid_qty": last[("fut", symbol)]["bid_qty"],
                    "fut_ask_qty": last[("fut", symbol)]["ask_qty"],
                    "spot_mid": spot_mid,
                    "fut_mid": fut_mid,
                    "basis_abs": basis_abs,
                    "basis_pct": basis_pct,
                    "collected_at": datetime.now(timezone.utc),
                }

                snapshot_to_db_5s.append(params_5s)

            bucket_10s = floor_10s(recv_ts)

            if last_flush != bucket_10s:

                print(f"[flush] 5s={len(snapshot_to_db_5s)} 1m={len(snapshot_to_db_1m)}")
                with engine.begin() as conn:
                    
                    if len(snapshot_to_db_5s) != 0:

                        text_sql_5s(snapshot_to_db_5s, conn)
                    
                    if len(snapshot_to_db_1m) != 0:

                        text_sql_1m(snapshot_to_db_1m, conn)

                snapshot_to_db_5s.clear()
                snapshot_to_db_1m.clear()
                last_flush = bucket_10s

        finally:
            queue.task_done()

async def main():
    q = asyncio.Queue(maxsize=200_000)
    await asyncio.gather(
        ws_consumer("spot", SPOT_URL, q),
        ws_consumer("fut",  FUT_URL,  q),
        processor(q),
    )

if __name__ == "__main__":
    
    asyncio.run(main())

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable
from config import DB_URL, SYMBOLS

from sqlalchemy import create_engine


from app.core.orderbook_bbo_snapshots.order_book import run_ws_orderbook_bbo 
from app.core.paper_trading.positions import refresh_open_positions  
from app.core.paper_trading.positions_cashflow import apply_funding_cashflows 
from app.core.funding_collector.funding_events import update_funding_events
from app.core.funding_collector.funding_stats_daily import get_funding_stats
from app.core.premium_index_snapshots.prem_index import update_premium_index  
from app.core.symbols.seeder import seed_symbols


@dataclass
class RunnerConfig:
    db_url: str
    symbols: list[str]
    dry_run: bool = True

    
    refresh_positions_every: float = 1.0
    apply_funding_every: float = 30.0
    update_funding_every: float = 60.0
    update_premium_every: float = 10.0
    seed_symbols_every: float = 24 * 3600
    funding_stats_every: float = 10.0


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def forever(name: str, coro_factory: Callable[[], Awaitable[None]], restart_delay: float = 2.0):
    
    log = logging.getLogger(f"runner.{name}")
    while True:
        try:
            log.info("task started")
            await coro_factory()
        except asyncio.CancelledError:
            log.info("task cancelled")
            raise
        except Exception:
            log.exception("task crashed, restarting in %.1fs", restart_delay)
            await asyncio.sleep(restart_delay)


async def periodic(
    name: str,
    fn: Callable[[], None],
    every: float,
    run_immediately: bool = True,
):
    
    log = logging.getLogger(f"runner.{name}")
    loop = asyncio.get_running_loop()

    if run_immediately:
        try:
            await loop.run_in_executor(None, fn)
        except Exception:
            log.exception("periodic run failed")

    while True:
        await asyncio.sleep(every)
        try:
            await loop.run_in_executor(None, fn)
            
        except Exception:
            log.exception("periodic run failed")



async def main(cfg: RunnerConfig):

    log = logging.getLogger("runner")
    engine = create_engine(
    cfg.db_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=2,
    )

    async def ws_task():

        await run_ws_orderbook_bbo(engine=engine, SYMBOLS=cfg.symbols)
        
    
    def refresh_positions_job():

        refresh_open_positions(engine=engine)

    def apply_funding_job():

        apply_funding_cashflows(engine, SYMBOLS = cfg.symbols)
        
    
    def update_funding_job():

        update_funding_events(engine, SYMBOLS=cfg.symbols)
        

    def update_premium_job():

        update_premium_index(engine, SYMBOLS=cfg.symbols)
        

    def seed_symbols_job():

        seed_symbols(engine, SYMBOLS=cfg.symbols)
    
    def get_funding_stats_job():

        get_funding_stats(engine=engine, SYMBOLS=cfg.symbols)

    log.info("Starting runner | dry_run=%s | symbols=%s", cfg.symbols)

    tasks = [
        asyncio.create_task(forever("ws_orderbook_bbo", lambda: ws_task())),
        asyncio.create_task(periodic("refresh_positions", refresh_positions_job, every=cfg.refresh_positions_every)),
        asyncio.create_task(periodic("apply_funding", apply_funding_job, every=cfg.apply_funding_every)),
        asyncio.create_task(periodic("update_funding_events", update_funding_job, every=cfg.update_funding_every)),
        asyncio.create_task(periodic("update_premium_index", update_premium_job, every=cfg.update_premium_every)),
        asyncio.create_task(periodic("seed_symbols", seed_symbols_job, every=cfg.seed_symbols_every, run_immediately=True)),
        asyncio.create_task(periodic("funding_stats", get_funding_stats_job, every=cfg.funding_stats_every, run_immediately=True))

    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("runner shutdown complete")


if __name__ == "__main__":
    setup_logging()

    cfg = RunnerConfig(
        db_url=DB_URL,
        symbols=SYMBOLS,
    )

    asyncio.run(main(cfg))
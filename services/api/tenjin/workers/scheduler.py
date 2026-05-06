"""Long-running scheduler — runs all adapters every N seconds.

Run as: `python -m tenjin.workers.scheduler`
"""

import asyncio
import os

import structlog

from tenjin.workers.scrape import run_all

log = structlog.get_logger(__name__)

INTERVAL_SECONDS = int(os.environ.get("SCRAPE_INTERVAL_SECONDS", "300"))  # 5 min default


async def loop() -> None:
    log.info("scheduler.started", interval_s=INTERVAL_SECONDS)
    while True:
        try:
            results = await run_all()
            total = sum(results.values())
            log.info("scheduler.tick_done", total_new=total, by_source=results)
        except Exception as e:
            log.error("scheduler.tick_failed", error=str(e))
        await asyncio.sleep(INTERVAL_SECONDS)


def main() -> None:
    asyncio.run(loop())


if __name__ == "__main__":
    main()

"""Scrape worker — fetches every adapter, persists results."""

import asyncio

import structlog

from tenjin.db.session import SessionLocal
from tenjin.pipeline.persist import persist_items
from tenjin.pipeline.prune import prune_old_articles
from tenjin.sources.base import SourceAdapter
from tenjin.sources.feeds import FEEDS
from tenjin.topics import presets, registry

log = structlog.get_logger(__name__)


async def run_adapter(adapter: SourceAdapter) -> int:
    """Fetch from an adapter, persist, return count of new articles."""
    items = await adapter.fetch()
    log.info("adapter.fetched", source=adapter.name, count=len(items))
    if not items:
        return 0

    if not registry.all_topics():
        presets.install()

    async with SessionLocal() as session:
        new_count = await persist_items(session, items)
    log.info("adapter.persisted", source=adapter.name, new=new_count)
    return new_count


async def run_all() -> dict[str, int]:
    """Run every configured feed in FEEDS sequentially. Returns {name: new_count}."""
    results: dict[str, int] = {}
    for adapter in FEEDS:
        try:
            results[adapter.name] = await run_adapter(adapter)
        except Exception as e:
            log.error("adapter.run_failed", source=adapter.name, error=str(e))
            results[adapter.name] = 0
    try:
        await prune_old_articles()
    except Exception as e:
        log.error("scrape.prune_failed", error=str(e))
    return results


def main() -> None:
    """Entry point for `python -m tenjin.workers.scrape` — single batch run."""
    results = asyncio.run(run_all())
    log.info("scrape.complete", results=results)


if __name__ == "__main__":
    main()

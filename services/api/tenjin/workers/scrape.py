"""RQ jobs invoked by `rq worker scrape`."""

import asyncio

import structlog

from tenjin.sources.base import SourceAdapter
from tenjin.sources.feeds import FEEDS

log = structlog.get_logger(__name__)


def run_adapter(adapter: SourceAdapter) -> int:
    """Fetch from an adapter, run the pipeline, persist. Returns count of new articles."""
    items = asyncio.run(adapter.fetch())
    log.info("adapter.fetched", source=adapter.name, count=len(items))
    # TODO: normalize → dedupe → topic-match → upsert → publish
    return 0


def run_all() -> dict[str, int]:
    """Run every configured feed in FEEDS. Returns {adapter_name: new_article_count}."""
    results = {}
    for adapter in FEEDS:
        try:
            results[adapter.name] = run_adapter(adapter)
        except Exception as e:
            log.error("adapter.run_failed", source=adapter.name, error=str(e))
            results[adapter.name] = 0
    return results

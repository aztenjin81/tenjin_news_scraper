"""RQ jobs invoked by `rq worker scrape`."""

import asyncio

import structlog

from tenjin.sources.base import SourceAdapter

log = structlog.get_logger(__name__)


def run_adapter(adapter: SourceAdapter) -> int:
    """Fetch from an adapter, run the pipeline, persist. Returns count of new articles."""
    items = asyncio.run(adapter.fetch())
    log.info("adapter.fetched", source=adapter.name, count=len(items))
    # TODO: normalize → dedupe → topic-match → upsert → publish
    return 0

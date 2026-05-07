"""Periodic data hygiene — drop articles older than the pipeline's max age."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete

from tenjin.db.session import SessionLocal
from tenjin.models import Article, FeedFetchLog
from tenjin.pipeline.persist import MAX_AGE

log = structlog.get_logger(__name__)


async def prune_old_articles() -> int:
    """Delete articles whose published_at is older than MAX_AGE. Returns rowcount."""
    cutoff = datetime.now(UTC) - MAX_AGE
    async with SessionLocal() as session:
        result = await session.execute(delete(Article).where(Article.published_at < cutoff))
        await session.commit()
    deleted = result.rowcount or 0
    if deleted:
        log.info("prune.dropped", count=deleted, cutoff=cutoff.isoformat())
    return deleted


async def prune_old_fetch_logs(max_age_days: int = 30) -> int:
    """Delete feed_fetch_log rows older than max_age_days. Returns rowcount."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    async with SessionLocal() as session:
        result = await session.execute(delete(FeedFetchLog).where(FeedFetchLog.fetched_at < cutoff))
        await session.commit()
    deleted = result.rowcount or 0
    if deleted:
        log.info("prune.fetch_logs_dropped", count=deleted, cutoff=cutoff.isoformat())
    return deleted

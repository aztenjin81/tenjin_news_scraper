"""Periodic data hygiene — drop articles older than the pipeline's max age."""

from datetime import UTC, datetime

import structlog
from sqlalchemy import delete

from tenjin.db.session import SessionLocal
from tenjin.models import Article
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

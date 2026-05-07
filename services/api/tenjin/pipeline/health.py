"""Per-fetch telemetry capture and (later) feed-health classification."""

from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from tenjin.models import FeedFetchLog

log = structlog.get_logger(__name__)


async def record_fetch(
    session: AsyncSession,
    *,
    source: str,
    fetched_at: datetime,
    duration_ms: int,
    http_status: int | None,
    error_kind: str,
    items_yielded: int,
    items_persisted: int,
) -> None:
    """Insert one feed_fetch_log row and commit. Best-effort: a failed insert
    must not propagate — telemetry shouldn't break scraping."""
    try:
        session.add(
            FeedFetchLog(
                source=source,
                fetched_at=fetched_at,
                duration_ms=duration_ms,
                http_status=http_status,
                error_kind=error_kind,
                items_yielded=items_yielded,
                items_persisted=items_persisted,
            )
        )
        await session.commit()
    except Exception as e:
        log.warning("health.record_fetch_failed", source=source, error=str(e))
        await session.rollback()

"""Per-fetch telemetry capture and (later) feed-health classification."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

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


Cadence = Literal["fast", "normal", "slow", "rare"]
Status = Literal["ok", "lagging", "silent"]

CADENCE_INTERVALS: dict[Cadence, timedelta] = {
    "fast": timedelta(minutes=30),
    "normal": timedelta(hours=2),
    "slow": timedelta(hours=12),
    "rare": timedelta(days=3),
}

ERROR_STREAK_THRESHOLD = 5


@dataclass(frozen=True, slots=True)
class FeedHealth:
    name: str
    label: str
    kind: str
    cadence: Cadence
    last_item_at: datetime | None
    items_24h: int
    status: Status


@dataclass(frozen=True, slots=True)
class FeedHealthReport:
    summary: dict[str, int]
    feeds: list[FeedHealth]
    generated_at: datetime


def classify(
    *,
    cadence: Cadence,
    last_item_at: datetime | None,
    recent_error_streak: int,
) -> Status:
    """Status for one feed. Errors override age — five consecutive failed
    fetches mean silent regardless of when the last item arrived."""
    if recent_error_streak >= ERROR_STREAK_THRESHOLD:
        return "silent"
    if last_item_at is None:
        return "silent"
    interval = CADENCE_INTERVALS[cadence]
    age = datetime.now(UTC) - last_item_at
    if age <= interval:
        return "ok"
    if age <= 3 * interval:
        return "lagging"
    return "silent"

"""Per-fetch telemetry capture and (later) feed-health classification."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import structlog
from sqlalchemy import desc, func, select
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


def _canonical_feeds():
    """Iterate the configured feed list. Returns adapter instances with
    name / outlet / source_kind / cadence. Wrapped in a function so tests
    can monkeypatch it without touching FEEDS."""
    from tenjin.sources.feeds import FEEDS  # late import to avoid cycles

    return list(FEEDS)


async def _recent_error_streaks(session: AsyncSession, names: list[str]) -> dict[str, int]:
    """For each source, count the consecutive error rows from newest backwards
    until the first non-error row (or until the configured threshold).
    Returns {source: streak_length}."""
    out: dict[str, int] = {}
    if not names:
        return out
    for name in names:
        rows = (
            (
                await session.execute(
                    select(FeedFetchLog.error_kind)
                    .where(FeedFetchLog.source == name)
                    .order_by(desc(FeedFetchLog.fetched_at))
                    .limit(ERROR_STREAK_THRESHOLD)
                )
            )
            .scalars()
            .all()
        )
        streak = 0
        for kind in rows:
            if kind == "none":
                break
            streak += 1
        out[name] = streak
    return out


async def compute_feed_health(session: AsyncSession) -> FeedHealthReport:
    """Read aggregated telemetry and produce a FeedHealthReport."""
    feeds = _canonical_feeds()
    names = [f.name for f in feeds]

    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)
    agg_q = (
        select(
            FeedFetchLog.source,
            func.max(FeedFetchLog.fetched_at)
            .filter(FeedFetchLog.items_persisted > 0)
            .label("last_item_at"),
            func.coalesce(
                func.sum(FeedFetchLog.items_persisted).filter(
                    FeedFetchLog.fetched_at >= cutoff_24h
                ),
                0,
            ).label("items_24h"),
        )
        .where(FeedFetchLog.source.in_(names))
        .group_by(FeedFetchLog.source)
    )
    agg_rows = (await session.execute(agg_q)).all()
    agg = {r.source: (r.last_item_at, int(r.items_24h)) for r in agg_rows}

    streaks = await _recent_error_streaks(session, names)

    feeds_out: list[FeedHealth] = []
    for f in feeds:
        last_item_at, items_24h = agg.get(f.name, (None, 0))
        status = classify(
            cadence=f.cadence,
            last_item_at=last_item_at,
            recent_error_streak=streaks.get(f.name, 0),
        )
        feeds_out.append(
            FeedHealth(
                name=f.name,
                label=getattr(f, "outlet", f.name),
                kind=f.source_kind,
                cadence=f.cadence,
                last_item_at=last_item_at,
                items_24h=items_24h,
                status=status,
            )
        )

    rank = {"silent": 0, "lagging": 1, "ok": 2}
    feeds_out.sort(key=lambda fh: (rank[fh.status], fh.label.lower()))

    summary = {
        "total": len(feeds_out),
        "ok": sum(1 for fh in feeds_out if fh.status == "ok"),
        "lagging": sum(1 for fh in feeds_out if fh.status == "lagging"),
        "silent": sum(1 for fh in feeds_out if fh.status == "silent"),
    }

    return FeedHealthReport(summary=summary, feeds=feeds_out, generated_at=now)

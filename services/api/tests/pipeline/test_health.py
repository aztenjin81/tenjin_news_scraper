"""Tests for pipeline.health. Skipped automatically when Postgres isn't reachable."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine

from tenjin.config import get_settings
from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.pipeline.health import record_fetch


async def _db_reachable() -> bool:
    try:
        engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        async with engine.connect():
            await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture
async def _clean_fetch_log():
    if not await _db_reachable():
        pytest.skip("Postgres not reachable")
    async with SessionLocal() as session:
        await session.execute(delete(FeedFetchLog).where(FeedFetchLog.source.like("test-%")))
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(delete(FeedFetchLog).where(FeedFetchLog.source.like("test-%")))
        await session.commit()


async def test_record_fetch_inserts_one_row(_clean_fetch_log):
    fetched_at = datetime.now(UTC) - timedelta(seconds=1)
    async with SessionLocal() as session:
        await record_fetch(
            session,
            source="test-source",
            fetched_at=fetched_at,
            duration_ms=42,
            http_status=200,
            error_kind="none",
            items_yielded=5,
            items_persisted=3,
        )
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(FeedFetchLog).where(FeedFetchLog.source == "test-source")
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    row = rows[0]
    assert row.source == "test-source"
    assert row.duration_ms == 42
    assert row.http_status == 200
    assert row.error_kind == "none"
    assert row.items_yielded == 5
    assert row.items_persisted == 3


from datetime import UTC, datetime, timedelta

from tenjin.pipeline.health import classify, FeedHealth


def _now():
    return datetime.now(UTC)


def test_classify_ok_within_one_cadence():
    last = _now() - timedelta(minutes=10)
    status = classify(cadence="fast", last_item_at=last, recent_error_streak=0)
    assert status == "ok"


def test_classify_lagging_between_one_and_three_cadences():
    last = _now() - timedelta(hours=1, minutes=30)  # fast = 30 min; 1.5h is between 1x and 3x
    status = classify(cadence="fast", last_item_at=last, recent_error_streak=0)
    assert status == "lagging"


def test_classify_silent_beyond_three_cadences():
    last = _now() - timedelta(hours=4)
    status = classify(cadence="fast", last_item_at=last, recent_error_streak=0)
    assert status == "silent"


def test_classify_silent_when_no_last_item():
    status = classify(cadence="normal", last_item_at=None, recent_error_streak=0)
    assert status == "silent"


def test_classify_silent_when_five_consecutive_errors():
    last = _now() - timedelta(minutes=2)  # would be ok by cadence
    status = classify(cadence="fast", last_item_at=last, recent_error_streak=5)
    assert status == "silent"


def test_classify_ok_when_four_errors_then_recovery():
    last = _now() - timedelta(minutes=2)
    status = classify(cadence="fast", last_item_at=last, recent_error_streak=4)
    assert status == "ok"

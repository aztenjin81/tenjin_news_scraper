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


@pytest.fixture(autouse=True)
async def _clean_fetch_log():
    if not await _db_reachable():
        pytest.skip("Postgres not reachable")
    async with SessionLocal() as session:
        await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.source.like("test-%"))
        )
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.source.like("test-%"))
        )
        await session.commit()


async def test_record_fetch_inserts_one_row():
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
            await session.execute(
                select(FeedFetchLog).where(FeedFetchLog.source == "test-source")
            )
        ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.source == "test-source"
    assert row.duration_ms == 42
    assert row.http_status == 200
    assert row.error_kind == "none"
    assert row.items_yielded == 5
    assert row.items_persisted == 3

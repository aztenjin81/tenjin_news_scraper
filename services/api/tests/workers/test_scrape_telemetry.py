"""Tests for the run_adapter telemetry wrapper. Skipped when Postgres unreachable."""

from dataclasses import dataclass

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine

from tenjin.config import get_settings
from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.sources.base import RawItem
from tenjin.workers.scrape import run_adapter


async def _db_reachable() -> bool:
    try:
        engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        async with engine.connect():
            await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
async def _clean_telemetry():
    if not await _db_reachable():
        pytest.skip("Postgres not reachable")
    async with SessionLocal() as session:
        await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.source.in_(["fake", "raising"]))
        )
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.source.in_(["fake", "raising"]))
        )
        await session.commit()


@dataclass
class _FakeAdapter:
    name: str = "fake"
    source_kind: str = "wire"
    cadence: str = "normal"

    async def fetch(self) -> list[RawItem]:
        return [
            RawItem(
                url="https://e.example/a",
                title="A",
                outlet="Fake",
                source_kind=self.source_kind,
            )
        ]


@dataclass
class _RaisingAdapter:
    name: str = "raising"
    source_kind: str = "wire"
    cadence: str = "normal"

    async def fetch(self) -> list[RawItem]:
        raise httpx.TimeoutException("simulated")


async def test_run_adapter_records_success():
    await run_adapter(_FakeAdapter())
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(FeedFetchLog).where(FeedFetchLog.source == "fake")
            )
        ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.error_kind == "none"
    assert row.items_yielded == 1
    assert row.items_persisted >= 0
    assert row.duration_ms >= 0


async def test_run_adapter_records_timeout():
    await run_adapter(_RaisingAdapter())
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(FeedFetchLog)
                .where(FeedFetchLog.source == "raising")
                .order_by(FeedFetchLog.fetched_at.desc())
                .limit(1)
            )
        ).scalars().all()
    assert len(rows) == 1
    assert rows[0].error_kind == "timeout"
    assert rows[0].items_yielded == 0
    assert rows[0].http_status is None

# Operational Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land a public `/sources` page that shows per-feed health (`ok` / `lagging` / `silent`) for OSINT-style coverage transparency, backed by a new `feed_fetch_log` telemetry table.

**Architecture:** Two PRs. **A**) Add the `FeedFetchLog` model + Alembic migration; add a `cadence` attribute on each adapter; record one row per fetch attempt from the worker; extend the prune pass. **B**) Health classifier in `pipeline/health.py`, `/sources` endpoint with 30-second in-process cache, public Next.js page (`app/sources/page.tsx`) via the same same-origin proxy pattern as `/api/articles`, nav link.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, Alembic, asyncpg, structlog, pytest, pytest-asyncio. Next.js 16 App Router, TypeScript, Tailwind v4.

**Source spec:** `docs/superpowers/specs/2026-05-06-operational-visibility-design.md`

---

## File Structure

### PR A — Telemetry capture and cadence config

- **Create:** `services/api/tenjin/models/fetch_log.py` — `FeedFetchLog` ORM model
- **Modify:** `services/api/tenjin/models/__init__.py` — export `FeedFetchLog`
- **Create:** `services/api/tenjin/db/migrations/versions/<rev>_add_feed_fetch_log.py` — Alembic migration
- **Modify:** `services/api/tenjin/sources/base.py` — add `cadence` to `SourceAdapter` Protocol
- **Modify:** `services/api/tenjin/sources/rss.py` — add `cadence: str = "normal"` field
- **Modify:** `services/api/tenjin/sources/hackernews.py` — add `cadence: str = "fast"` field on `HackerNewsAdapter`
- **Modify:** `services/api/tenjin/sources/feeds.py` — extend `_rss` / `_reddit` helpers; assign cadence to every feed
- **Create:** `services/api/tenjin/pipeline/health.py` — `record_fetch()` helper (classifier comes in PR B)
- **Modify:** `services/api/tenjin/workers/scrape.py` — wrap `run_adapter` with telemetry capture
- **Modify:** `services/api/tenjin/pipeline/prune.py` — `prune_old_fetch_logs()`
- **Modify:** `services/api/tenjin/api/app.py` — call `prune_old_fetch_logs` from lifespan startup
- **Create:** `services/api/tests/pipeline/test_health.py` — record_fetch test
- **Modify:** `services/api/tests/test_pipeline.py` — `prune_old_fetch_logs` test
- **Modify:** `services/api/tests/sources/test_feeds.py` — assert every feed has a valid cadence
- **Modify:** `services/api/tests/sources/test_rss.py` — cadence default + override test
- **Create:** `services/api/tests/workers/__init__.py`
- **Create:** `services/api/tests/workers/test_scrape_telemetry.py` — wrapper records on success / timeout / http error

### PR B — Health classifier, `/sources` endpoint, public page

- **Modify:** `services/api/tenjin/pipeline/health.py` — `FeedHealth`, `FeedHealthReport`, `compute_feed_health()`, classification rule
- **Create:** `services/api/tenjin/api/schemas/health.py` — `FeedHealthOut`, `FeedHealthReportOut`
- **Create:** `services/api/tenjin/api/routes/sources.py` — `GET /sources` with 30-second TTL cache
- **Modify:** `services/api/tenjin/api/app.py` — register the new router
- **Modify:** `services/api/tests/pipeline/test_health.py` — classify + compute tests
- **Create:** `services/api/tests/test_sources_route.py` — endpoint shape + cache test
- **Modify:** `apps/web/lib/api.ts` — `FeedHealth`, `FeedHealthReport` types + `fetchSources()`
- **Modify:** `apps/web/lib/fixtures.ts` — `FIXTURE_SOURCES_REPORT` for offline dev
- **Modify:** `apps/web/lib/sources.ts` — re-use existing `SourceKind` taxonomy (no change expected; verify)
- **Create:** `apps/web/app/api/sources/route.ts` — same-origin proxy
- **Create:** `apps/web/components/StatusDot.tsx` — small status indicator component
- **Create:** `apps/web/app/sources/page.tsx` — SSR page (B layout: counts hero, silent/lagging sections, full grouped list)
- **Modify:** `apps/web/components/Header.tsx` — add "Sources" nav link
- **Modify:** `apps/web/app/globals.css` — add `--status-ok`, `--status-warn`, `--status-bad` tokens
- **Create:** `apps/web/app/sources/page.test.tsx` — vitest snapshot rendering against the fixture report

---

## Conventions to follow

- **Branches:** `claude/<short-description>`. Code goes on a branch and ships via PR. Per `feedback_direct_to_main_for_docs` only docs land on main directly; this is production code.
- **Commits within a branch:** imperative, scoped subject (`api: add feed_fetch_log model`, `web: add sources page`).
- **Adapters:** must not raise on transient errors — log and return `[]`. The wrapping `run_adapter` is the safety net for what escapes (hard parse crashes, etc.).
- **Routes:** thin. Logic lives in `pipeline/health.py`.
- **Schemas vs models:** never return ORM objects from a route. Pydantic in `api/schemas/`.
- **Settings:** all env access via `tenjin.config.Settings`.
- **No new client-state library on web.** SSR + ISR. No `"use client"` at the page root.

---

# PR A — Telemetry capture and cadence config

Branch: `claude/api-feed-fetch-log`. Off `main`.

### Task A1: Create the `FeedFetchLog` SQLAlchemy model

**Files:**
- Create: `services/api/tenjin/models/fetch_log.py`
- Modify: `services/api/tenjin/models/__init__.py`

- [ ] **Step 1: Create the branch.**

```bash
git checkout main
git pull
git checkout -b claude/api-feed-fetch-log
```

- [ ] **Step 2: Write the model.**

```python
# services/api/tenjin/models/fetch_log.py
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tenjin.models.base import Base


class FeedFetchLog(Base):
    """One row per scrape-worker fetch attempt. Drives the public /sources page
    and (later) the internal /admin view. Pruned at 30 days by pipeline/prune.py.
    """

    __tablename__ = "feed_fetch_log"
    __table_args__ = (
        Index("ix_feed_fetch_log_source_fetched_at", "source", "fetched_at"),
        Index("ix_feed_fetch_log_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    items_yielded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_persisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

- [ ] **Step 3: Re-export from the `models` package.**

```python
# services/api/tenjin/models/__init__.py
# Add (alongside the existing exports):
from tenjin.models.fetch_log import FeedFetchLog  # noqa: F401
```

Confirm the existing `__init__.py` already re-exports `Article`, `Topic`, `TopicMatch`. If `__all__` is defined, append `"FeedFetchLog"`.

- [ ] **Step 4: Commit.**

```bash
git add services/api/tenjin/models/fetch_log.py services/api/tenjin/models/__init__.py
git commit -m "api: add FeedFetchLog model"
```

---

### Task A2: Generate and review the Alembic migration

**Files:**
- Create: `services/api/tenjin/db/migrations/versions/<rev>_add_feed_fetch_log.py`

- [ ] **Step 1: Generate the migration.**

```bash
cd services/api
alembic revision --autogenerate -m "add feed_fetch_log"
```

Alembic prints the revision ID and the file path. Open the new file under `tenjin/db/migrations/versions/`.

- [ ] **Step 2: Review the autogenerated migration. It should look like this — adjust if Alembic produced anything different (extra index ordering quirks are fine; spurious index drops on unrelated tables are not).**

```python
"""add feed_fetch_log

Revision ID: <generated>
Revises: 0f42abaa8399
Create Date: <generated>

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "<generated>"
down_revision: Union[str, Sequence[str], None] = "0f42abaa8399"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feed_fetch_log",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_kind", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("items_yielded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_persisted", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feed_fetch_log_source_fetched_at",
        "feed_fetch_log",
        ["source", "fetched_at"],
    )
    op.create_index(
        "ix_feed_fetch_log_fetched_at",
        "feed_fetch_log",
        ["fetched_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feed_fetch_log_fetched_at", table_name="feed_fetch_log")
    op.drop_index("ix_feed_fetch_log_source_fetched_at", table_name="feed_fetch_log")
    op.drop_table("feed_fetch_log")
```

The `server_default` values exist so the migration is safe on a populated database (no rows yet, but defensive). The model itself sets Python-side defaults too, so insert paths don't depend on the server defaults.

- [ ] **Step 3: Apply the migration locally.**

```bash
cd services/api
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 0f42abaa8399 -> <rev>, add feed_fetch_log`. No errors.

- [ ] **Step 4: Verify the table exists.**

```bash
docker compose -f ../../infra/docker-compose.yml exec postgres \
  psql -U tenjin -d tenjin -c "\d feed_fetch_log"
```

Expected: table description listing `id`, `source`, `fetched_at`, `duration_ms`, `http_status`, `error_kind`, `items_yielded`, `items_persisted`, plus the two indexes.

- [ ] **Step 5: Commit.**

```bash
git add services/api/tenjin/db/migrations/versions/<rev>_add_feed_fetch_log.py
git commit -m "api: alembic migration for feed_fetch_log"
```

---

### Task A3: Add `cadence` field to adapters

**Files:**
- Modify: `services/api/tenjin/sources/base.py`
- Modify: `services/api/tenjin/sources/rss.py`
- Modify: `services/api/tenjin/sources/hackernews.py`
- Modify: `services/api/tests/sources/test_rss.py`

- [ ] **Step 1: Write the failing test.**

```python
# services/api/tests/sources/test_rss.py — add at the bottom:
def test_rss_adapter_default_cadence_is_normal():
    from tenjin.sources.rss import RssAdapter
    a = RssAdapter(name="x", feed_url="http://e.example", outlet="X", source_kind="wire")
    assert a.cadence == "normal"


def test_rss_adapter_cadence_override():
    from tenjin.sources.rss import RssAdapter
    a = RssAdapter(
        name="x",
        feed_url="http://e.example",
        outlet="X",
        source_kind="wire",
        cadence="fast",
    )
    assert a.cadence == "fast"


def test_hackernews_adapter_default_cadence_is_fast():
    from tenjin.sources.hackernews import HackerNewsAdapter
    a = HackerNewsAdapter()
    assert a.cadence == "fast"
```

- [ ] **Step 2: Run, verify it fails.**

```bash
cd services/api
pytest tests/sources/test_rss.py::test_rss_adapter_default_cadence_is_normal -v
```

Expected: `AttributeError: 'RssAdapter' object has no attribute 'cadence'`.

- [ ] **Step 3: Add `cadence` to the `SourceAdapter` Protocol (documentation; concrete classes provide the value).**

```python
# services/api/tenjin/sources/base.py
class SourceAdapter(Protocol):
    """One adapter per source family (rss, html-outlet, gdelt, x, reddit, ...).

    Adapters must not raise on transient errors. Log and return [] instead — the
    worker treats partial collection as normal.
    """

    name: str
    cadence: str  # "fast" | "normal" | "slow" | "rare" — expected new-content interval

    async def fetch(self) -> list[RawItem]: ...
```

- [ ] **Step 4: Add the field to `RssAdapter`.**

```python
# services/api/tenjin/sources/rss.py — inside the @dataclass:
@dataclass
@register("rss")
class RssAdapter(SourceAdapter):
    """Generic RSS/Atom adapter. One instance per feed URL."""

    name: str
    feed_url: str
    outlet: str
    source_kind: str = "wire"
    paywall: bool = False
    cadence: str = "normal"
    user_agent: str = _DEFAULT_UA
```

(Order matters: dataclass fields without defaults must precede fields with defaults. `cadence` after `paywall` and before `user_agent` is fine since both have defaults.)

- [ ] **Step 5: Add the field to `HackerNewsAdapter`.**

```python
# services/api/tenjin/sources/hackernews.py — inside HackerNewsAdapter:
@dataclass
@register("hackernews")
class HackerNewsAdapter(SourceAdapter):
    """Top stories from the Hacker News Firebase API. No credentials required."""

    name: str = "hackernews"
    source_kind: str = "social"
    cadence: str = "fast"
    limit: int = field(default=50)
```

- [ ] **Step 6: Run, verify all three tests pass.**

```bash
pytest tests/sources/test_rss.py -v
```

Expected: all `test_rss_adapter_*` and `test_hackernews_adapter_*` tests pass; existing tests in the file still pass.

- [ ] **Step 7: Commit.**

```bash
git add services/api/tenjin/sources/base.py \
        services/api/tenjin/sources/rss.py \
        services/api/tenjin/sources/hackernews.py \
        services/api/tests/sources/test_rss.py
git commit -m "api: add cadence attribute to source adapters"
```

---

### Task A4: Wire cadence into `feeds.py` helpers and assign per-feed buckets

**Files:**
- Modify: `services/api/tenjin/sources/feeds.py`
- Modify: `services/api/tests/sources/test_feeds.py`

- [ ] **Step 1: Write the failing test.**

```python
# services/api/tests/sources/test_feeds.py — append:
def test_all_feeds_have_valid_cadence():
    from tenjin.sources.feeds import FEEDS
    valid = {"fast", "normal", "slow", "rare"}
    for adapter in FEEDS:
        assert hasattr(adapter, "cadence"), f"{adapter.name} missing cadence"
        assert adapter.cadence in valid, (
            f"{adapter.name} has unknown cadence {adapter.cadence!r}"
        )
```

- [ ] **Step 2: Run, verify it fails.**

```bash
cd services/api
pytest tests/sources/test_feeds.py::test_all_feeds_have_valid_cadence -v
```

Expected: fails because the existing `_rss(...)` and `_reddit(...)` helpers don't set `cadence` — adapters take the default ("normal" or "fast"), which actually makes the test *pass* but with all-default values. So extend the test to assert variety:

```python
def test_feeds_use_multiple_cadences():
    from tenjin.sources.feeds import FEEDS
    used = {a.cadence for a in FEEDS}
    assert {"fast", "slow"}.issubset(used), (
        f"feeds.py should use varied cadences; got {used}"
    )
```

Run again:

```bash
pytest tests/sources/test_feeds.py::test_feeds_use_multiple_cadences -v
```

Expected: fails — `assert {'fast', 'slow'}.issubset({'normal'})` is false.

- [ ] **Step 3: Update the helpers to take `cadence` and assign per-feed buckets.**

Update the helpers at the top of `feeds.py`:

```python
# services/api/tenjin/sources/feeds.py — replace the helpers:
def _reddit(slug: str, *, cadence: str = "fast") -> RssAdapter:
    return RssAdapter(
        name=f"reddit-{slug}",
        feed_url=f"{_R}/{slug}/.rss",
        outlet=f"r/{slug}",
        source_kind="social",
        cadence=cadence,
    )


def _rss(
    name: str,
    url: str,
    outlet: str,
    kind: str,
    *,
    paywall: bool = False,
    cadence: str = "normal",
) -> RssAdapter:
    return RssAdapter(
        name=name,
        feed_url=url,
        outlet=outlet,
        source_kind=kind,
        paywall=paywall,
        cadence=cadence,
    )
```

- [ ] **Step 4: Assign cadence to every existing entry. Use these defaults; tweak per outlet only when you have a specific reason.**

  - **Wire** (Reuters/AP/NPR/PBS/NBC/CBS/ABC, Al Jazeera English): `cadence="fast"`
  - **Reddit feeds**: keep helper default (`fast`).
  - **HackerNewsAdapter**: keep its instance default (`fast`).
  - **Regional** (Times of Israel, Haaretz, Arab News, The Cradle, Kyiv Independent, Ukrainska Pravda, Euromaidan Press, Meduza, Moscow Times, Notes from Poland): `cadence="normal"`.
  - **State** (Tehran Times, Press TV, IRNA, TASS, RT, Al Mayadeen, Kremlin.ru): `cadence="slow"` for ministerial/state outlets that publish in slower bursts.
  - **Primary** (US State Dept, US CENTCOM, US DoD, ReliefWeb): `cadence="slow"`.
  - **IAEA** specifically: `cadence="rare"` (often quiet for days).
  - **Analysis** (ISW, Brookings Foreign Policy, Atlantic Council UkraineAlert, CSIS, RUSI, War on the Rocks): `cadence="slow"`.

Concrete edits — go through every entry and add `cadence=...`. Example:

```python
    _rss(
        "ap-world",
        "https://apnews.com/index.rss",
        "AP",
        "wire",
        cadence="fast",
    ),
    ...
    _rss(
        "tehran-times",
        "https://www.tehrantimes.com/rss",
        "Tehran Times",
        "state",
        cadence="slow",
    ),
    ...
    _rss(
        "iaea",
        "https://www.iaea.org/news/feed",
        "IAEA",
        "primary",
        cadence="rare",
    ),
    ...
    _rss(
        "isw",
        "https://www.understandingwar.org/news/feed",
        "Institute for the Study of War",
        "analysis",
        cadence="slow",
    ),
```

You don't have to touch `_reddit(...)` calls — the default is `fast`, which is the right value for the subreddits in `feeds.py`.

- [ ] **Step 5: Run all feed tests.**

```bash
pytest tests/sources/test_feeds.py -v
```

Expected: every test passes, including the two new ones.

- [ ] **Step 6: Commit.**

```bash
git add services/api/tenjin/sources/feeds.py services/api/tests/sources/test_feeds.py
git commit -m "api: assign cadence buckets to every configured feed"
```

---

### Task A5: `pipeline/health.py` with `record_fetch()`

**Files:**
- Create: `services/api/tenjin/pipeline/health.py`
- Create: `services/api/tests/pipeline/test_health.py`

- [ ] **Step 1: Write the failing test.**

```python
# services/api/tests/pipeline/test_health.py
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.pipeline.health import record_fetch


@pytest.mark.asyncio
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
        # record_fetch commits; re-query in a fresh session
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
```

- [ ] **Step 2: Run, verify it fails.**

```bash
cd services/api
pytest tests/pipeline/test_health.py::test_record_fetch_inserts_one_row -v
```

Expected: `ImportError: cannot import name 'record_fetch' from 'tenjin.pipeline.health'` (the module doesn't exist).

- [ ] **Step 3: Implement `record_fetch`.**

```python
# services/api/tenjin/pipeline/health.py
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
```

- [ ] **Step 4: Run, verify pass.**

```bash
pytest tests/pipeline/test_health.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit.**

```bash
git add services/api/tenjin/pipeline/health.py services/api/tests/pipeline/test_health.py
git commit -m "api: pipeline.health.record_fetch — telemetry insert helper"
```

---

### Task A6: Wrap `run_adapter` with telemetry capture

**Files:**
- Modify: `services/api/tenjin/workers/scrape.py`
- Create: `services/api/tests/workers/__init__.py`
- Create: `services/api/tests/workers/test_scrape_telemetry.py`

- [ ] **Step 1: Create the empty test package init.**

```python
# services/api/tests/workers/__init__.py
```

- [ ] **Step 2: Write the failing test (success path + transport-error path).**

```python
# services/api/tests/workers/test_scrape_telemetry.py
from dataclasses import dataclass

import httpx
import pytest
from sqlalchemy import select

from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.sources.base import RawItem
from tenjin.workers.scrape import run_adapter


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


@pytest.mark.asyncio
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
    # items_persisted may be 0 if the article already exists in the test DB
    # from a prior run; assert >= 0 to keep the test idempotent.
    assert row.items_persisted >= 0
    assert row.duration_ms >= 0


@pytest.mark.asyncio
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
```

- [ ] **Step 3: Run, verify failure.**

```bash
cd services/api
pytest tests/workers/test_scrape_telemetry.py -v
```

Expected: tests fail because `run_adapter` doesn't insert log rows yet, and the `_RaisingAdapter` test fails because the existing `run_all` catches but `run_adapter` itself doesn't.

- [ ] **Step 4: Replace `run_adapter` in `services/api/tenjin/workers/scrape.py`.**

```python
"""Scrape worker — fetches every adapter, persists results, records telemetry."""

import time
from datetime import UTC, datetime

import httpx
import structlog

from tenjin.db.session import SessionLocal
from tenjin.pipeline.health import record_fetch
from tenjin.pipeline.persist import persist_items
from tenjin.sources.base import SourceAdapter
from tenjin.sources.feeds import FEEDS
from tenjin.topics import presets, registry

log = structlog.get_logger(__name__)


async def run_adapter(adapter: SourceAdapter) -> int:
    """Fetch from an adapter, persist, record telemetry, return new article count."""
    started_at = datetime.now(UTC)
    started_mono = time.monotonic()
    error_kind = "none"
    http_status: int | None = None
    items_yielded = 0
    items_persisted = 0

    try:
        items = await adapter.fetch()
        items_yielded = len(items)
        log.info("adapter.fetched", source=adapter.name, count=items_yielded)

        if items:
            if not registry.all_topics():
                presets.install()
            async with SessionLocal() as session:
                items_persisted = await persist_items(session, items)
            log.info("adapter.persisted", source=adapter.name, new=items_persisted)
    except httpx.TimeoutException:
        error_kind = "timeout"
        log.warning("adapter.timeout", source=adapter.name)
    except httpx.HTTPStatusError as e:
        http_status = e.response.status_code
        error_kind = "http_4xx" if 400 <= http_status < 500 else "http_5xx"
        log.warning("adapter.http_error", source=adapter.name, status=http_status)
    except httpx.HTTPError:
        error_kind = "transport"
        log.warning("adapter.transport_error", source=adapter.name)
    except Exception:
        error_kind = "transport"
        log.exception("adapter.unhandled", source=adapter.name)
    finally:
        duration_ms = int((time.monotonic() - started_mono) * 1000)
        async with SessionLocal() as session:
            await record_fetch(
                session,
                source=adapter.name,
                fetched_at=started_at,
                duration_ms=duration_ms,
                http_status=http_status,
                error_kind=error_kind,
                items_yielded=items_yielded,
                items_persisted=items_persisted,
            )

    return items_persisted
```

Notes for the implementer:
- The existing adapters already swallow most transient errors internally and return `[]` (RSS/HN do this). The `try/except` in `run_adapter` is the safety net for what escapes (a parse-time crash, an unhandled httpx exception). When an adapter returns `[]` cleanly, `items_yielded == 0` and `error_kind == "none"`, which is exactly what we want for distinguishing "feed parses but is quiet" from "feed errored."
- Telemetry write uses a *separate* session from `persist_items` so the log row commits even if persistence rolled back.

- [ ] **Step 5: Update `run_all` (no logic change — it already calls `run_adapter` and catches; the catch is now redundant for transport but kept as a final safety net).**

The existing `run_all` is fine as-is. No edit needed.

- [ ] **Step 6: Run, verify both tests pass.**

```bash
pytest tests/workers/test_scrape_telemetry.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Run the full suite to confirm nothing else broke.**

```bash
pytest -v
```

Expected: all tests pass. Existing scrape tests should be unaffected.

- [ ] **Step 8: Commit.**

```bash
git add services/api/tenjin/workers/scrape.py \
        services/api/tests/workers/__init__.py \
        services/api/tests/workers/test_scrape_telemetry.py
git commit -m "api: record per-fetch telemetry from run_adapter"
```

---

### Task A7: `prune_old_fetch_logs` and lifespan wiring

**Files:**
- Modify: `services/api/tenjin/pipeline/prune.py`
- Modify: `services/api/tenjin/api/app.py`
- Modify: `services/api/tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_pipeline.py` or use an existing prune-test file).**

```python
# services/api/tests/test_pipeline.py — append:
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.pipeline.prune import prune_old_fetch_logs


@pytest.mark.asyncio
async def test_prune_old_fetch_logs_drops_only_old_rows():
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        session.add_all([
            FeedFetchLog(
                source="prune-test", fetched_at=now - timedelta(days=10),
                duration_ms=1, error_kind="none",
            ),
            FeedFetchLog(
                source="prune-test", fetched_at=now - timedelta(days=25),
                duration_ms=1, error_kind="none",
            ),
            FeedFetchLog(
                source="prune-test", fetched_at=now - timedelta(days=45),
                duration_ms=1, error_kind="none",
            ),
        ])
        await session.commit()

    deleted = await prune_old_fetch_logs(max_age_days=30)
    assert deleted == 1

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(FeedFetchLog).where(FeedFetchLog.source == "prune-test")
            )
        ).scalars().all()
    assert len(rows) == 2
```

- [ ] **Step 2: Run, verify failure (`ImportError`).**

```bash
pytest tests/test_pipeline.py::test_prune_old_fetch_logs_drops_only_old_rows -v
```

- [ ] **Step 3: Add `prune_old_fetch_logs` to `pipeline/prune.py`.**

```python
# services/api/tenjin/pipeline/prune.py — append:
from tenjin.models import FeedFetchLog


async def prune_old_fetch_logs(max_age_days: int = 30) -> int:
    """Delete feed_fetch_log rows older than max_age_days. Returns rowcount."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    async with SessionLocal() as session:
        result = await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.fetched_at < cutoff)
        )
        await session.commit()
    deleted = result.rowcount or 0
    if deleted:
        log.info("prune.fetch_logs_dropped", count=deleted, cutoff=cutoff.isoformat())
    return deleted
```

You'll need to import `timedelta` at the top of the file (the existing import is `from datetime import UTC, datetime`).

```python
# services/api/tenjin/pipeline/prune.py — top imports:
from datetime import UTC, datetime, timedelta
```

- [ ] **Step 4: Wire into the FastAPI lifespan startup.**

```python
# services/api/tenjin/api/app.py — extend the lifespan body:
from tenjin.pipeline.prune import prune_old_articles, prune_old_fetch_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await install_topics()
        log.info("app.topics_installed")
    except Exception as e:
        log.warning("app.topic_install_failed", error=str(e))
    try:
        deleted = await prune_old_articles()
        log.info("app.prune_complete", deleted=deleted)
    except Exception as e:
        log.warning("app.prune_failed", error=str(e))
    try:
        deleted = await prune_old_fetch_logs()
        log.info("app.prune_fetch_logs_complete", deleted=deleted)
    except Exception as e:
        log.warning("app.prune_fetch_logs_failed", error=str(e))
    yield
```

- [ ] **Step 5: Run, verify pass.**

```bash
pytest tests/test_pipeline.py::test_prune_old_fetch_logs_drops_only_old_rows -v
```

- [ ] **Step 6: Commit.**

```bash
git add services/api/tenjin/pipeline/prune.py \
        services/api/tenjin/api/app.py \
        services/api/tests/test_pipeline.py
git commit -m "api: prune feed_fetch_log rows older than 30 days on startup"
```

---

### Task A8: Push branch and open PR A

- [ ] **Step 1: Run the entire test suite.**

```bash
cd services/api
pytest -v
```

Expected: all green.

- [ ] **Step 2: Push and open the PR.**

```bash
git push -u origin claude/api-feed-fetch-log
gh pr create --title "api: feed_fetch_log telemetry + per-feed cadence" \
  --body "$(cat <<'EOF'
PR A of the operational visibility spec (docs/superpowers/specs/2026-05-06-operational-visibility-design.md).

- New \`feed_fetch_log\` table + Alembic migration; one row per fetch attempt.
- Adapter cadence attribute (fast / normal / slow / rare); assigned per feed in \`feeds.py\`.
- \`pipeline.health.record_fetch()\` writes one row in its own session.
- \`workers.scrape.run_adapter\` records on success, timeout, http error, transport.
- 30-day retention via \`pipeline.prune.prune_old_fetch_logs\`, called from FastAPI lifespan.

No /sources page yet — PR B reads this telemetry. Production behavior is unchanged for current readers.
EOF
)"
```

---

# PR B — Health classifier, `/sources` endpoint, public page

Branch: `claude/api-sources-page`. Off `main` after PR A merges (depends on the model + cadence config from PR A).

### Task B1: Health dataclasses and classify rule

**Files:**
- Modify: `services/api/tenjin/pipeline/health.py`
- Modify: `services/api/tests/pipeline/test_health.py`

- [ ] **Step 1: Branch off latest main (after PR A merged).**

```bash
git checkout main
git pull
git checkout -b claude/api-sources-page
```

- [ ] **Step 2: Write the failing classify tests.**

```python
# services/api/tests/pipeline/test_health.py — append:
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
```

- [ ] **Step 3: Run, verify failure.**

```bash
cd services/api
pytest tests/pipeline/test_health.py -v
```

Expected: ImportError on `classify` and `FeedHealth`.

- [ ] **Step 4: Add the classifier and dataclasses to `pipeline/health.py`.**

```python
# services/api/tenjin/pipeline/health.py — append at the top of the file
# (below existing imports, before record_fetch):

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

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
```

- [ ] **Step 5: Run, verify pass.**

```bash
pytest tests/pipeline/test_health.py -v
```

Expected: all classify tests pass; existing `record_fetch` test still passes.

- [ ] **Step 6: Commit.**

```bash
git add services/api/tenjin/pipeline/health.py services/api/tests/pipeline/test_health.py
git commit -m "api: feed health dataclasses + classify rule"
```

---

### Task B2: `compute_feed_health` — SQL aggregation + report build

**Files:**
- Modify: `services/api/tenjin/pipeline/health.py`
- Modify: `services/api/tests/pipeline/test_health.py`

- [ ] **Step 1: Write the failing integration test.**

```python
# services/api/tests/pipeline/test_health.py — append:
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from tenjin.db.session import SessionLocal
from tenjin.models import FeedFetchLog
from tenjin.pipeline.health import compute_feed_health


@pytest.mark.asyncio
async def test_compute_feed_health_classifies_known_feeds(monkeypatch):
    # Patch the canonical feed list so this test is hermetic.
    from tenjin.pipeline import health as health_mod

    @dataclass
    class _F:
        name: str
        outlet: str
        source_kind: str
        cadence: str

    fake_feeds = [
        _F(name="cf-fast-ok", outlet="Fast OK", source_kind="wire", cadence="fast"),
        _F(name="cf-fast-silent", outlet="Fast Silent", source_kind="wire", cadence="fast"),
        _F(name="cf-rare-zero", outlet="Rare Zero", source_kind="primary", cadence="rare"),
    ]
    monkeypatch.setattr(health_mod, "_canonical_feeds", lambda: fake_feeds)

    now = datetime.now(UTC)
    async with SessionLocal() as session:
        await session.execute(
            delete(FeedFetchLog).where(FeedFetchLog.source.like("cf-%"))
        )
        session.add_all([
            FeedFetchLog(
                source="cf-fast-ok", fetched_at=now - timedelta(minutes=5),
                duration_ms=1, error_kind="none",
                items_yielded=2, items_persisted=2,
            ),
            FeedFetchLog(
                source="cf-fast-silent", fetched_at=now - timedelta(hours=10),
                duration_ms=1, error_kind="none",
                items_yielded=1, items_persisted=1,
            ),
            # cf-rare-zero: no rows at all — should classify as silent
        ])
        await session.commit()

    async with SessionLocal() as session:
        report = await compute_feed_health(session)

    by_name = {f.name: f for f in report.feeds}
    assert by_name["cf-fast-ok"].status == "ok"
    assert by_name["cf-fast-silent"].status == "silent"
    assert by_name["cf-rare-zero"].status == "silent"
    assert by_name["cf-rare-zero"].last_item_at is None
    assert report.summary["total"] == 3
    assert report.summary["silent"] == 2
    assert report.summary["ok"] == 1
    # Ordering: silent before ok
    assert report.feeds[0].status in {"silent"}
    assert report.feeds[-1].status == "ok"


from dataclasses import dataclass  # noqa: E402  (placed after the test for readability)
```

The test uses a `monkeypatch` of an internal helper `_canonical_feeds()` so it doesn't depend on the actual `feeds.py` list. Patching is tidier than touching real production data in tests.

- [ ] **Step 2: Run, verify failure.**

```bash
pytest tests/pipeline/test_health.py::test_compute_feed_health_classifies_known_feeds -v
```

- [ ] **Step 3: Implement `_canonical_feeds`, the SQL helper, and `compute_feed_health` in `pipeline/health.py`.**

```python
# services/api/tenjin/pipeline/health.py — append:

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenjin.sources.feeds import FEEDS


def _canonical_feeds():
    """Iterate the configured feed list. Yields adapter-like objects with
    name / outlet (or label) / source_kind / cadence. Wrapped in a function
    so tests can monkeypatch it without touching FEEDS."""
    return list(FEEDS)


async def compute_feed_health(session: AsyncSession) -> FeedHealthReport:
    """Read aggregated telemetry and produce a FeedHealthReport."""
    feeds = _canonical_feeds()
    names = [f.name for f in feeds]

    # One round-trip: per-source last-item time + items in last 24h.
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)
    agg_q = (
        select(
            FeedFetchLog.source,
            func.max(FeedFetchLog.fetched_at).filter(
                FeedFetchLog.items_persisted > 0
            ).label("last_item_at"),
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

    # Per-source recent error streak: how many of the most recent rows have
    # error_kind != 'none', counted from newest until the first 'none'.
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

    # Sort: silent, lagging, ok; alphabetical within each group.
    rank = {"silent": 0, "lagging": 1, "ok": 2}
    feeds_out.sort(key=lambda f: (rank[f.status], f.label.lower()))

    summary = {
        "total": len(feeds_out),
        "ok": sum(1 for f in feeds_out if f.status == "ok"),
        "lagging": sum(1 for f in feeds_out if f.status == "lagging"),
        "silent": sum(1 for f in feeds_out if f.status == "silent"),
    }

    return FeedHealthReport(summary=summary, feeds=feeds_out, generated_at=now)


async def _recent_error_streaks(
    session: AsyncSession, names: list[str]
) -> dict[str, int]:
    """For each source, count the consecutive error rows from newest backwards
    until the first non-error row (or the configured threshold).
    Returns {source: streak_length}."""
    out: dict[str, int] = {}
    if not names:
        return out
    for name in names:
        rows = (
            await session.execute(
                select(FeedFetchLog.error_kind)
                .where(FeedFetchLog.source == name)
                .order_by(desc(FeedFetchLog.fetched_at))
                .limit(ERROR_STREAK_THRESHOLD)
            )
        ).scalars().all()
        streak = 0
        for kind in rows:
            if kind == "none":
                break
            streak += 1
        out[name] = streak
    return out
```

- [ ] **Step 4: Run, verify pass.**

```bash
pytest tests/pipeline/test_health.py -v
```

Expected: all green. The error-streak tests added in Task B1 are still useful and still pass.

- [ ] **Step 5: Commit.**

```bash
git add services/api/tenjin/pipeline/health.py services/api/tests/pipeline/test_health.py
git commit -m "api: pipeline.health.compute_feed_health"
```

---

### Task B3: `/sources` route + Pydantic schema + 30-second cache

**Files:**
- Create: `services/api/tenjin/api/schemas/health.py`
- Create: `services/api/tenjin/api/routes/sources.py`
- Modify: `services/api/tenjin/api/app.py`
- Create: `services/api/tests/test_sources_route.py`

- [ ] **Step 1: Write the failing test.**

```python
# services/api/tests/test_sources_route.py
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tenjin.api.app import create_app
from tenjin.pipeline.health import FeedHealth, FeedHealthReport


@pytest.fixture
def report():
    return FeedHealthReport(
        summary={"total": 2, "ok": 1, "lagging": 0, "silent": 1},
        feeds=[
            FeedHealth(
                name="alpha", label="Alpha", kind="wire", cadence="fast",
                last_item_at=None, items_24h=0, status="silent",
            ),
            FeedHealth(
                name="beta", label="Beta", kind="wire", cadence="fast",
                last_item_at=datetime.now(UTC) - timedelta(minutes=5),
                items_24h=12, status="ok",
            ),
        ],
        generated_at=datetime.now(UTC),
    )


def test_sources_endpoint_shape(report):
    app = create_app()
    with patch(
        "tenjin.api.routes.sources.compute_feed_health",
        new=AsyncMock(return_value=report),
    ):
        client = TestClient(app)
        # Bypass the cache for this test by clearing it.
        from tenjin.api.routes import sources as routes_mod
        routes_mod._cache_clear()
        resp = client.get("/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == {"total": 2, "ok": 1, "lagging": 0, "silent": 1}
    assert len(data["feeds"]) == 2
    f0 = data["feeds"][0]
    assert set(f0.keys()) == {
        "name", "label", "kind", "cadence", "last_item_at", "items_24h", "status",
    }


def test_sources_endpoint_caches(report):
    from tenjin.api.routes import sources as routes_mod
    routes_mod._cache_clear()

    mock_compute = AsyncMock(return_value=report)
    app = create_app()
    with patch("tenjin.api.routes.sources.compute_feed_health", new=mock_compute):
        client = TestClient(app)
        client.get("/sources")
        client.get("/sources")
    assert mock_compute.call_count == 1
```

- [ ] **Step 2: Run, verify failure.**

```bash
cd services/api
pytest tests/test_sources_route.py -v
```

Expected: 404 (route not registered).

- [ ] **Step 3: Add the Pydantic schemas.**

```python
# services/api/tenjin/api/schemas/health.py
from datetime import datetime

from pydantic import BaseModel


class FeedHealthOut(BaseModel):
    name: str
    label: str
    kind: str
    cadence: str
    last_item_at: datetime | None
    items_24h: int
    status: str


class FeedHealthReportOut(BaseModel):
    summary: dict[str, int]
    feeds: list[FeedHealthOut]
    generated_at: datetime
```

- [ ] **Step 4: Add the route with a 30-second TTL cache.**

```python
# services/api/tenjin/api/routes/sources.py
import time
from typing import Any

from fastapi import APIRouter

from tenjin.api.deps import SessionDep
from tenjin.api.schemas.health import FeedHealthOut, FeedHealthReportOut
from tenjin.pipeline.health import compute_feed_health

router = APIRouter()

_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {"value": None, "expires_at": 0.0}


def _cache_clear() -> None:
    _cache["value"] = None
    _cache["expires_at"] = 0.0


@router.get("", response_model=FeedHealthReportOut)
async def get_sources(session: SessionDep) -> FeedHealthReportOut:
    now = time.monotonic()
    if _cache["value"] is not None and now < _cache["expires_at"]:
        return _cache["value"]

    report = await compute_feed_health(session)
    out = FeedHealthReportOut(
        summary=report.summary,
        feeds=[
            FeedHealthOut(
                name=f.name,
                label=f.label,
                kind=f.kind,
                cadence=f.cadence,
                last_item_at=f.last_item_at,
                items_24h=f.items_24h,
                status=f.status,
            )
            for f in report.feeds
        ],
        generated_at=report.generated_at,
    )

    _cache["value"] = out
    _cache["expires_at"] = now + _CACHE_TTL_SECONDS
    return out
```

- [ ] **Step 5: Register the router.**

```python
# services/api/tenjin/api/app.py — extend the imports and include_router calls:
from tenjin.api.routes import articles, health, sources, stream, topics
...
def create_app() -> FastAPI:
    ...
    app.include_router(health.router)
    app.include_router(articles.router, prefix="/articles", tags=["articles"])
    app.include_router(topics.router, prefix="/topics", tags=["topics"])
    app.include_router(stream.router, prefix="/stream", tags=["stream"])
    app.include_router(sources.router, prefix="/sources", tags=["sources"])
    return app
```

- [ ] **Step 6: Run, verify pass.**

```bash
pytest tests/test_sources_route.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Smoke-test against a running API.**

```bash
docker compose -f infra/docker-compose.yml up -d
cd services/api
uvicorn tenjin.api.app:app --reload &
curl -sS http://localhost:8000/sources | jq .summary
```

Expected: JSON with `total`, `ok`, `lagging`, `silent`. After at least one scrape tick, counts will be non-zero. Stop the dev server when done.

- [ ] **Step 8: Commit.**

```bash
git add services/api/tenjin/api/schemas/health.py \
        services/api/tenjin/api/routes/sources.py \
        services/api/tenjin/api/app.py \
        services/api/tests/test_sources_route.py
git commit -m "api: GET /sources endpoint with 30s in-process cache"
```

---

### Task B4: Web — `lib/api.ts` types + fetcher + fixture

**Files:**
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/fixtures.ts`

- [ ] **Step 1: Add types and fetcher to `lib/api.ts`.**

```typescript
// apps/web/lib/api.ts — append at the bottom:
export type FeedStatus = "ok" | "lagging" | "silent";
export type FeedCadence = "fast" | "normal" | "slow" | "rare";

export type FeedHealth = {
  name: string;
  label: string;
  kind: string;
  cadence: FeedCadence;
  last_item_at: string | null;
  items_24h: number;
  status: FeedStatus;
};

export type FeedHealthReport = {
  summary: { total: number; ok: number; lagging: number; silent: number };
  feeds: FeedHealth[];
  generated_at: string;
};

export async function fetchSources(): Promise<FeedHealthReport> {
  try {
    const res = await fetch(`${API_BASE_URL}/sources`, {
      next: { revalidate: 30 },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn("[api] fetchSources fallback to fixtures:", e);
    const { FIXTURE_SOURCES_REPORT } = await import("./fixtures");
    return FIXTURE_SOURCES_REPORT;
  }
}
```

`API_BASE_URL` is the existing constant in this file (used by `fetchArticles` etc.). Keep the same import shape.

- [ ] **Step 2: Add the fixture for offline dev.**

```typescript
// apps/web/lib/fixtures.ts — append:
import type { FeedHealthReport } from "./api";

export const FIXTURE_SOURCES_REPORT: FeedHealthReport = {
  summary: { total: 5, ok: 3, lagging: 1, silent: 1 },
  feeds: [
    {
      name: "idf-spokesperson",
      label: "IDF Spokesperson",
      kind: "primary",
      cadence: "rare",
      last_item_at: null,
      items_24h: 0,
      status: "silent",
    },
    {
      name: "tehran-times",
      label: "Tehran Times",
      kind: "state",
      cadence: "slow",
      last_item_at: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
      items_24h: 4,
      status: "lagging",
    },
    {
      name: "ap-world",
      label: "AP",
      kind: "wire",
      cadence: "fast",
      last_item_at: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
      items_24h: 47,
      status: "ok",
    },
    {
      name: "al-jazeera",
      label: "Al Jazeera",
      kind: "regional",
      cadence: "normal",
      last_item_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
      items_24h: 28,
      status: "ok",
    },
    {
      name: "isw",
      label: "Institute for the Study of War",
      kind: "analysis",
      cadence: "slow",
      last_item_at: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(),
      items_24h: 1,
      status: "ok",
    },
  ],
  generated_at: new Date().toISOString(),
};
```

- [ ] **Step 3: Commit.**

```bash
git add apps/web/lib/api.ts apps/web/lib/fixtures.ts
git commit -m "web: FeedHealthReport types, fetchSources, fixture"
```

---

### Task B5: Web — same-origin proxy

**Files:**
- Create: `apps/web/app/api/sources/route.ts`

- [ ] **Step 1: Write the proxy.**

```typescript
// apps/web/app/api/sources/route.ts
/**
 * Same-origin proxy for the FastAPI /sources endpoint. Mirrors the pattern
 * used by /api/articles. Browser stays same-origin; the internal API URL
 * isn't exposed.
 */
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const revalidate = 30;

const UPSTREAM =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest): Promise<Response> {
  const upstream = await fetch(`${UPSTREAM}/sources`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 30 },
    signal: req.signal,
  });
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=30",
    },
  });
}
```

- [ ] **Step 2: Smoke-test the proxy.**

```bash
cd apps/web
pnpm dev
# in another shell
curl -sS http://localhost:3000/api/sources | jq .summary
```

Expected: same JSON shape as the FastAPI endpoint.

- [ ] **Step 3: Commit.**

```bash
git add apps/web/app/api/sources/route.ts
git commit -m "web: same-origin /api/sources proxy"
```

---

### Task B6: Web — status colors and `StatusDot` component

**Files:**
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/components/StatusDot.tsx`

- [ ] **Step 1: Add status color tokens in `globals.css`.**

Find the `:root` block where the existing `--accent` etc. tokens live. Append:

```css
/* Operational status — used by /sources */
--status-ok: oklch(0.78 0.18 150);     /* green */
--status-warn: oklch(0.85 0.17 80);    /* amber */
--status-bad: oklch(0.72 0.20 25);     /* red-orange */
```

If your `globals.css` uses Tailwind v4's `@theme` block, add the tokens there as well so utility classes can reference them:

```css
@theme {
  --color-status-ok: var(--status-ok);
  --color-status-warn: var(--status-warn);
  --color-status-bad: var(--status-bad);
}
```

- [ ] **Step 2: Write the `StatusDot` component.**

```typescript
// apps/web/components/StatusDot.tsx
import type { FeedStatus } from "@/lib/api";

const COLOR: Record<FeedStatus, string> = {
  ok: "var(--status-ok)",
  lagging: "var(--status-warn)",
  silent: "var(--status-bad)",
};

export function StatusDot({ status }: { status: FeedStatus }) {
  return (
    <span
      aria-label={status}
      className="inline-block h-2 w-2 rounded-full align-middle"
      style={{ backgroundColor: COLOR[status] }}
    />
  );
}
```

- [ ] **Step 3: Commit.**

```bash
git add apps/web/app/globals.css apps/web/components/StatusDot.tsx
git commit -m "web: status color tokens + StatusDot component"
```

---

### Task B7: Web — `/sources` page (status-first layout)

**Files:**
- Create: `apps/web/app/sources/page.tsx`

- [ ] **Step 1: Write the page.**

```typescript
// apps/web/app/sources/page.tsx
import type { Metadata } from "next";

import { StatusDot } from "@/components/StatusDot";
import {
  fetchSources,
  type FeedHealth,
  type FeedHealthReport,
  type FeedStatus,
} from "@/lib/api";

export const revalidate = 30;

export const metadata: Metadata = {
  title: "Sources — Tenjin News",
  description:
    "Every feed Tenjin News tracks, with current health and last-fetch time. Coverage transparency for OSINT-leaning readers.",
  alternates: { canonical: "/sources" },
};

export default async function SourcesPage() {
  const report = await fetchSources();
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <p className="text-xs uppercase tracking-wider text-[var(--muted)]">
          Sources · {report.summary.total} tracked · updated{" "}
          {timeAgo(report.generated_at)}
        </p>
        <h1 className="mt-3 font-serif text-[44px] leading-tight">Sources</h1>
        <p className="mt-3 max-w-prose text-[var(--foreground-2)]">
          Every feed we track. Updated continuously. Status reflects how recently
          each source has produced content relative to its expected cadence.
        </p>
      </header>

      <SummaryCards summary={report.summary} />
      <ProblemSection
        title="Silent"
        feeds={report.feeds.filter((f) => f.status === "silent")}
        emptyMessage="Nothing silent right now."
      />
      <ProblemSection
        title="Lagging"
        feeds={report.feeds.filter((f) => f.status === "lagging")}
        emptyMessage="Nothing lagging."
      />
      <FullList feeds={report.feeds} />
    </main>
  );
}

function SummaryCards({ summary }: { summary: FeedHealthReport["summary"] }) {
  const cards: Array<{ label: string; value: number; tone: FeedStatus }> = [
    { label: "OK", value: summary.ok, tone: "ok" },
    { label: "Lagging", value: summary.lagging, tone: "lagging" },
    { label: "Silent", value: summary.silent, tone: "silent" },
  ];
  const toneToVar: Record<FeedStatus, string> = {
    ok: "var(--status-ok)",
    lagging: "var(--status-warn)",
    silent: "var(--status-bad)",
  };
  return (
    <section className="mb-10 grid grid-cols-3 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="border border-white/10 px-4 py-3"
          style={{ borderColor: `color-mix(in oklch, ${toneToVar[c.tone]} 35%, transparent)` }}
        >
          <div className="text-2xl font-medium" style={{ color: toneToVar[c.tone] }}>
            {c.value}
          </div>
          <div className="mt-1 text-xs uppercase tracking-wider text-[var(--muted)]">
            {c.label}
          </div>
        </div>
      ))}
    </section>
  );
}

function ProblemSection({
  title,
  feeds,
  emptyMessage,
}: {
  title: string;
  feeds: FeedHealth[];
  emptyMessage: string;
}) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-xs uppercase tracking-wider text-[var(--muted)]">
        {title} · {feeds.length}
      </h2>
      {feeds.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{emptyMessage}</p>
      ) : (
        <ul className="divide-y divide-white/10 border border-white/10">
          {feeds.map((f) => (
            <FeedRow key={f.name} feed={f} />
          ))}
        </ul>
      )}
    </section>
  );
}

const KIND_ORDER = ["wire", "regional", "primary", "state", "analysis", "social"] as const;

function FullList({ feeds }: { feeds: FeedHealth[] }) {
  const grouped: Record<string, FeedHealth[]> = {};
  for (const f of feeds) {
    (grouped[f.kind] ??= []).push(f);
  }
  for (const list of Object.values(grouped)) {
    list.sort((a, b) => a.label.localeCompare(b.label));
  }

  return (
    <section>
      <h2 className="mb-3 text-xs uppercase tracking-wider text-[var(--muted)]">
        All sources · {feeds.length}
      </h2>
      <div className="space-y-6">
        {KIND_ORDER.filter((k) => grouped[k]?.length).map((kind) => (
          <div key={kind}>
            <h3 className="mb-2 text-xs uppercase tracking-wider text-[var(--muted)]">
              {kind} · {grouped[kind].length}
            </h3>
            <ul className="divide-y divide-white/10 border border-white/10">
              {grouped[kind].map((f) => (
                <FeedRow key={f.name} feed={f} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeedRow({ feed }: { feed: FeedHealth }) {
  return (
    <li className="flex items-center justify-between gap-4 px-3 py-2 text-sm">
      <div className="min-w-0 flex-1 truncate">{feed.label}</div>
      <div className="text-xs text-[var(--muted)]">
        {feed.last_item_at ? timeAgo(feed.last_item_at) : "no items yet"}
      </div>
      <div className="w-16 text-right text-xs text-[var(--muted)]">
        {feed.items_24h} / 24h
      </div>
      <div className="flex w-16 items-center justify-end gap-1.5 text-xs">
        <StatusDot status={feed.status} />
        <span className="text-[var(--muted)]">{feed.status}</span>
      </div>
    </li>
  );
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}
```

- [ ] **Step 2: Smoke-test the page.**

```bash
cd apps/web
pnpm dev
# Visit http://localhost:3000/sources
```

Expected: page renders. With the API up and at least one scrape tick, real numbers; without it, the fixture (5 entries) renders.

- [ ] **Step 3: Commit.**

```bash
git add apps/web/app/sources/page.tsx
git commit -m "web: add /sources page (status-first layout)"
```

---

### Task B8: Web — nav link

**Files:**
- Modify: `apps/web/components/Header.tsx`

- [ ] **Step 1: Read the existing Header to find the nav structure.**

```bash
cat apps/web/components/Header.tsx
```

- [ ] **Step 2: Add a Link to `/sources` alongside the existing nav links.**

The Header file likely has an array of nav items or inline `<Link>` elements. Match the existing pattern. Sentence case, no emoji. Example shape if the file uses inline Links:

```tsx
<Link href="/sources" className="text-[var(--muted)] hover:text-[var(--foreground)]">
  Sources
</Link>
```

If the file uses an array:

```tsx
const NAV = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/sources", label: "Sources" },  // <-- new
];
```

- [ ] **Step 3: Smoke-test in the browser.**

```bash
cd apps/web
pnpm dev
# Click the Sources link in the header on http://localhost:3000
```

Expected: navigates to `/sources` and the page renders.

- [ ] **Step 4: Commit.**

```bash
git add apps/web/components/Header.tsx
git commit -m "web: nav link to /sources"
```

---

### Task B9: Web — page snapshot test

**Files:**
- Create: `apps/web/app/sources/page.test.tsx`

- [ ] **Step 1: Write a vitest test that renders the page against the fixture.**

```typescript
// apps/web/app/sources/page.test.tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import SourcesPage from "./page";
import { FIXTURE_SOURCES_REPORT } from "@/lib/fixtures";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSources: vi.fn(async () => FIXTURE_SOURCES_REPORT),
  };
});

describe("/sources page", () => {
  it("renders three count cards and the silent feed", async () => {
    render(await SourcesPage());

    // Eyebrow with total count
    expect(screen.getByText(/5 tracked/i)).toBeInTheDocument();

    // Three count tiles
    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("Lagging")).toBeInTheDocument();
    expect(screen.getByText("Silent")).toBeInTheDocument();

    // Silent section names the IDF Spokesperson fixture entry
    expect(screen.getByText("IDF Spokesperson")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run.**

```bash
cd apps/web
pnpm test app/sources/page.test.tsx
```

Expected: 1 passed.

If the project's vitest config doesn't yet support `await SourcesPage()` (RSC test), use `react-server-dom` test infra or rewrite the test to call `fetchSources()` directly and render the rest of the page tree manually. Match whatever pattern the existing web tests use; if there are none, this snapshot test is best-effort and can be skipped with a `it.skip` plus a note in the PR description.

- [ ] **Step 3: Commit.**

```bash
git add apps/web/app/sources/page.test.tsx
git commit -m "web: snapshot test for /sources page"
```

---

### Task B10: Push branch and open PR B

- [ ] **Step 1: Run all backend and frontend tests.**

```bash
cd services/api && pytest -v
cd ../../apps/web && pnpm test && pnpm typecheck
```

Expected: green on both sides.

- [ ] **Step 2: Push and open the PR.**

```bash
git push -u origin claude/api-sources-page
gh pr create --title "api+web: public /sources coverage transparency page" \
  --body "$(cat <<'EOF'
PR B of the operational visibility spec (docs/superpowers/specs/2026-05-06-operational-visibility-design.md).

Backend:
- pipeline/health.py: classify rule (ok/lagging/silent) + compute_feed_health
  using one filtered-aggregate SQL pass, plus per-source recent-error streak
  check.
- New /sources route with 30-second in-process cache; FeedHealthReportOut
  Pydantic schema.

Frontend:
- /sources page (Server Component, ISR revalidate=30) with the status-first
  layout: count tiles, silent + lagging sections, full list grouped by kind.
- Same-origin /api/sources proxy.
- StatusDot component, --status-{ok,warn,bad} tokens.
- Header nav link.

Public-facing — no auth. Exposes feed inventory, kind, last-item-ago, items
in last 24h. Internal /admin and silent-feed alerting are deferred to
follow-up specs that reuse the same telemetry.

Tests:
- Backend: classify (6 cases), compute_feed_health (integration), /sources
  endpoint (shape + cache).
- Web: snapshot test of the page rendering against the fixture.
EOF
)"
```

---

## Self-review notes (already applied)

While drafting this plan I found and corrected:

1. **`feeds.py` shape mismatch.** The spec described feeds as `(name, url, kind, cadence, topics)` tuples, but the actual `feeds.py` uses adapter *instances*. The plan reflects the real code — `cadence` is a constructor arg on `RssAdapter` / `HackerNewsAdapter` / `_reddit` / `_rss`, not a tuple element.
2. **Worker shape mismatch.** The spec showed `_run_one(feed, session)` style; the actual worker has `run_adapter(adapter)` that creates its own session. The plan rewrites `run_adapter` (not introduces `_run_one`) and uses a *separate* session for the telemetry insert so it commits independent of `persist_items`.
3. **Items-24h aggregation.** The spec's first wording said `COUNT(*) FILTER (...items_persisted > 0)` — that's "fetches that yielded items," not articles. The plan uses `SUM(items_persisted)` as corrected in the spec self-review.
4. **Error-streak ambiguity.** The plan's `_recent_error_streaks` function reads the most recent rows ordered by `fetched_at desc` regardless of error status, then counts the consecutive errors from newest backward — matching the corrected spec wording.

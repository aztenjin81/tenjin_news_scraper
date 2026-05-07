"""End-to-end tests for the persist pipeline against a real Postgres.

Skipped automatically if DATABASE_URL doesn't point at a reachable database.
CI provides one; local devs need `sudo docker compose -f infra/docker-compose.yml up -d`.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine

from tenjin.config import get_settings
from tenjin.db.bootstrap import install_topics
from tenjin.db.session import SessionLocal
from tenjin.models import Article, Topic, TopicMatch
from tenjin.pipeline.persist import persist_items
from tenjin.sources.base import RawItem
from tenjin.topics import presets


async def _db_reachable() -> bool:
    try:
        engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        async with engine.connect():
            await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
async def _clean_db():
    """Wipe articles and topic_matches before and after each test."""
    if not await _db_reachable():
        pytest.skip("Postgres not reachable")
    async with SessionLocal() as session:
        await session.execute(delete(TopicMatch))
        await session.execute(delete(Article))
        await session.commit()
    yield
    async with SessionLocal() as session:
        await session.execute(delete(TopicMatch))
        await session.execute(delete(Article))
        await session.commit()


async def test_persist_inserts_new_article():
    await install_topics()
    presets.install()
    items = [
        RawItem(
            url="https://example.com/iran-talks",
            title="Iran talks resume in Geneva",
            outlet="Reuters",
            source_kind="wire",
            published_at=datetime.now(UTC),
            body="Negotiators reconvene this week",
        )
    ]
    async with SessionLocal() as session:
        new = await persist_items(session, items)
        assert new == 1

        row = (await session.execute(select(Article))).scalar_one()
        assert row.title == "Iran talks resume in Geneva"
        assert row.source_kind == "wire"
        assert row.canonical_url == "https://example.com/iran-talks"
        assert row.snippet == "Negotiators reconvene this week"


async def test_persist_dedupes_on_canonical_url():
    await install_topics()
    presets.install()
    item = RawItem(
        url="https://example.com/story?utm_source=tw",
        title="Story",
        outlet="AP",
        source_kind="wire",
        published_at=datetime.now(UTC),
    )
    async with SessionLocal() as session:
        first = await persist_items(session, [item])
        # Same canonical url, different tracking params — should dedupe
        item2 = RawItem(
            url="https://example.com/story?utm_source=fb",
            title="Story (revised headline)",
            outlet="AP",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
        second = await persist_items(session, [item2])
        assert first == 1
        assert second == 0  # dedup on canonical_url

        rows = (await session.execute(select(Article))).scalars().all()
        assert len(rows) == 1
        # ON CONFLICT DO UPDATE should refresh the title
        assert rows[0].title == "Story (revised headline)"


async def test_persist_creates_topic_matches():
    await install_topics()
    presets.install()
    items = [
        RawItem(
            url="https://example.com/iran-irgc",
            title="IRGC commander makes statement on US sanctions",
            outlet="Reuters",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
    ]
    async with SessionLocal() as session:
        await persist_items(session, items)

        matches = (
            (
                await session.execute(
                    select(Topic.slug)
                    .join(TopicMatch, TopicMatch.topic_id == Topic.id)
                    .join(Article, Article.id == TopicMatch.article_id)
                )
            )
            .scalars()
            .all()
        )
        assert "iran-us" in matches


async def test_articles_sorted_by_published_then_fetched():
    """Regression: the API must order by COALESCE(published_at, fetched_at)
    so feeds processed sequentially don't cluster by source on the page."""
    from datetime import timedelta

    from fastapi.testclient import TestClient

    from tenjin.api.app import app

    await install_topics()
    presets.install()

    base = datetime.now(UTC) - timedelta(hours=2)
    # Note: feed A's items are persisted FIRST (so smaller fetched_at) but have
    # OLDER published_at; feed B's items are persisted SECOND but PUBLISHED
    # earlier. Correct behavior: results ordered purely by published_at desc.
    feed_a_items = [
        RawItem(
            url=f"https://a.example.com/{i}",
            title=f"Feed A item {i}",
            outlet="Feed A",
            source_kind="wire",
            published_at=base + timedelta(minutes=i),
        )
        for i in range(3)
    ]
    feed_b_items = [
        RawItem(
            url=f"https://b.example.com/{i}",
            title=f"Feed B item {i}",
            outlet="Feed B",
            source_kind="wire",
            published_at=base + timedelta(minutes=10 + i),
        )
        for i in range(3)
    ]
    async with SessionLocal() as session:
        await persist_items(session, feed_a_items)
        await persist_items(session, feed_b_items)

    with TestClient(app) as client:
        rows = client.get("/articles").json()
        titles = [r["title"] for r in rows]
        # Must be interleaved by published_at, not grouped by outlet
        # Expected order: B2, B1, B0, A2, A1, A0
        assert titles == [
            "Feed B item 2",
            "Feed B item 1",
            "Feed B item 0",
            "Feed A item 2",
            "Feed A item 1",
            "Feed A item 0",
        ], f"got {titles}"


async def test_persist_skips_items_without_url_or_title():
    await install_topics()
    presets.install()
    items = [
        RawItem(url="", title="No URL", outlet="x"),
        RawItem(url="https://example.com/no-title", title="", outlet="x"),
    ]
    async with SessionLocal() as session:
        new = await persist_items(session, items)
        assert new == 0
        rows = (await session.execute(select(Article))).scalars().all()
        assert rows == []


async def test_persist_drops_items_older_than_max_age():
    """Stale RSS feeds (e.g. dead Xinhua endpoint) emit articles from years
    ago. Pipeline must drop anything older than 30 days."""
    from datetime import timedelta

    from tenjin.pipeline.persist import MAX_AGE

    await install_topics()
    presets.install()

    fresh = datetime.now(UTC) - timedelta(days=1)
    ancient = datetime.now(UTC) - (MAX_AGE + timedelta(days=1))
    items = [
        RawItem(
            url="https://example.com/fresh",
            title="Fresh story",
            outlet="x",
            published_at=fresh,
        ),
        RawItem(
            url="https://example.com/ancient",
            title="Ancient story from 2017",
            outlet="x",
            published_at=ancient,
        ),
    ]
    async with SessionLocal() as session:
        new = await persist_items(session, items)
        assert new == 1
        urls = (await session.execute(select(Article.canonical_url))).scalars().all()
        assert urls == ["https://example.com/fresh"]


async def test_prune_old_articles_deletes_stale_rows():
    """Cleanup helper drops articles older than MAX_AGE."""
    from datetime import timedelta

    from tenjin.pipeline.persist import MAX_AGE
    from tenjin.pipeline.prune import prune_old_articles

    await install_topics()
    presets.install()

    fresh = datetime.now(UTC) - timedelta(days=1)
    ancient = datetime.now(UTC) - (MAX_AGE + timedelta(days=10))

    # Bypass persist_items' own age filter by inserting directly via the model
    async with SessionLocal() as session:
        session.add(
            Article(
                url="https://example.com/x",
                canonical_url="https://example.com/x",
                title="Stale row already in DB",
                outlet="x",
                source_kind="wire",
                published_at=ancient,
                fetched_at=fresh,
            )
        )
        session.add(
            Article(
                url="https://example.com/y",
                canonical_url="https://example.com/y",
                title="Recent row",
                outlet="x",
                source_kind="wire",
                published_at=fresh,
                fetched_at=fresh,
            )
        )
        await session.commit()

    deleted = await prune_old_articles()
    assert deleted == 1

    async with SessionLocal() as session:
        urls = (await session.execute(select(Article.canonical_url))).scalars().all()
        assert urls == ["https://example.com/y"]


async def test_prune_old_fetch_logs_drops_only_old_rows():
    """30-day retention on feed_fetch_log."""
    from datetime import timedelta

    from sqlalchemy import delete, select

    from tenjin.models import FeedFetchLog
    from tenjin.pipeline.prune import prune_old_fetch_logs

    now = datetime.now(UTC)
    async with SessionLocal() as session:
        await session.execute(delete(FeedFetchLog).where(FeedFetchLog.source == "prune-test"))
        session.add_all(
            [
                FeedFetchLog(
                    source="prune-test",
                    fetched_at=now - timedelta(days=10),
                    duration_ms=1,
                    error_kind="none",
                ),
                FeedFetchLog(
                    source="prune-test",
                    fetched_at=now - timedelta(days=25),
                    duration_ms=1,
                    error_kind="none",
                ),
                FeedFetchLog(
                    source="prune-test",
                    fetched_at=now - timedelta(days=45),
                    duration_ms=1,
                    error_kind="none",
                ),
            ]
        )
        await session.commit()

    deleted = await prune_old_fetch_logs(max_age_days=30)
    assert deleted == 1

    async with SessionLocal() as session:
        rows = (
            (await session.execute(select(FeedFetchLog).where(FeedFetchLog.source == "prune-test")))
            .scalars()
            .all()
        )
    assert len(rows) == 2

    # Cleanup so we don't leave test rows around
    async with SessionLocal() as session:
        await session.execute(delete(FeedFetchLog).where(FeedFetchLog.source == "prune-test"))
        await session.commit()

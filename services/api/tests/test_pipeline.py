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

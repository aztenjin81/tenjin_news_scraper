"""Verify newly-inserted articles get published to Redis pubsub channels per
matched topic, and that publish failure doesn't break persistence.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from tenjin.config import get_settings
from tenjin.db.bootstrap import install_topics
from tenjin.db.session import SessionLocal
from tenjin.models import Article, TopicMatch
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


async def test_publishes_new_article_to_matched_topics():
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

    fake_redis = AsyncMock()
    with patch("tenjin.pipeline.publish.get_redis", return_value=fake_redis):
        async with SessionLocal() as session:
            new = await persist_items(session, items)
            assert new == 1

    # Should have published once for each matched topic.
    assert fake_redis.publish.await_count >= 1
    channels = {call.args[0] for call in fake_redis.publish.await_args_list}
    assert "topic:iran-us" in channels

    # Payload must be valid JSON matching ArticleOut shape.
    sample = fake_redis.publish.await_args_list[0]
    payload = json.loads(sample.args[1])
    assert payload["title"] == "IRGC commander makes statement on US sanctions"
    assert payload["source_kind"] == "wire"
    assert "id" in payload
    assert "url" in payload


async def test_no_publish_on_dedup():
    """Re-inserting the same canonical_url is an UPDATE, not an INSERT, so
    no pubsub event should fire — subscribers shouldn't see ghost duplicates."""
    await install_topics()
    presets.install()

    item = RawItem(
        url="https://example.com/dup-story",
        title="A story about iran",
        outlet="AP",
        source_kind="wire",
        published_at=datetime.now(UTC),
    )

    fake_redis = AsyncMock()
    with patch("tenjin.pipeline.publish.get_redis", return_value=fake_redis):
        async with SessionLocal() as session:
            assert await persist_items(session, [item]) == 1
        first_call_count = fake_redis.publish.await_count

        async with SessionLocal() as session:
            assert await persist_items(session, [item]) == 0
        assert fake_redis.publish.await_count == first_call_count


async def test_publish_failure_does_not_break_persistence():
    """If Redis is down, articles must still land in the DB."""
    await install_topics()
    presets.install()

    items = [
        RawItem(
            url="https://example.com/redis-down",
            title="Iran sanctions package signed",
            outlet="AP",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
    ]

    fake_redis = AsyncMock()
    fake_redis.publish.side_effect = Exception("connection refused")

    with patch("tenjin.pipeline.publish.get_redis", return_value=fake_redis):
        async with SessionLocal() as session:
            new = await persist_items(session, items)
            assert new == 1


async def test_no_publish_when_no_topic_matches():
    """Articles that don't match any topic shouldn't trigger a pubsub call."""
    await install_topics()
    presets.install()

    items = [
        RawItem(
            url="https://example.com/random-tech",
            title="JavaScript framework releases new version",
            outlet="HN",
            source_kind="social",
            published_at=datetime.now(UTC),
        )
    ]

    fake_redis = AsyncMock()
    with patch("tenjin.pipeline.publish.get_redis", return_value=fake_redis):
        async with SessionLocal() as session:
            new = await persist_items(session, items)
            assert new == 1

    # Nothing matched — nothing published.
    assert fake_redis.publish.await_count == 0

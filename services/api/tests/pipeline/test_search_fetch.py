"""Tests for pipeline.search_fetch.fetch_for_query.

Best-effort: never raises. Failures of cache, lock, adapters, or persistence
all degrade silently — search itself returns DB results regardless.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from tenjin.pipeline.search_fetch import fetch_for_query
from tenjin.sources.base import RawItem


@pytest.fixture
def fake_redis():
    return AsyncMock()


@pytest.fixture
def fake_search_adapters():
    """Stub Google News + HN search adapters."""
    google = AsyncMock()
    google.search = AsyncMock(return_value=[])
    hn = AsyncMock()
    hn.search = AsyncMock(return_value=[])
    return google, hn


async def test_cache_hit_skips_fetch(fake_redis, fake_search_adapters):
    """When Redis has a recent cache entry for this query, no adapter is called."""
    google, hn = fake_search_adapters
    fake_redis.get = AsyncMock(return_value="1")  # cache hit

    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
    ):
        await fetch_for_query("phoenix shooting")

    google.search.assert_not_called()
    hn.search.assert_not_called()
    # Should not have tried to acquire the lock either.
    fake_redis.set.assert_not_called()


async def test_lock_contention_skips_fetch(fake_redis, fake_search_adapters):
    """If another worker holds the lock (SET NX returns falsy), don't run adapters."""
    google, hn = fake_search_adapters
    fake_redis.get = AsyncMock(return_value=None)         # cache miss
    fake_redis.set = AsyncMock(return_value=False)        # lock NOT acquired (NX failed)

    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
    ):
        await fetch_for_query("phoenix shooting")

    google.search.assert_not_called()
    hn.search.assert_not_called()


async def test_persists_results_from_both_adapters(fake_redis, fake_search_adapters):
    """Cache miss + lock acquired → both adapters run; their items go through persist_items."""
    google, hn = fake_search_adapters
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)
    fake_redis.delete = AsyncMock(return_value=1)
    google.search = AsyncMock(return_value=[
        RawItem(
            url="https://example.com/phoenix",
            title="Phoenix shooting",
            outlet="AZCentral",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
    ])
    hn.search = AsyncMock(return_value=[
        RawItem(
            url="https://example.com/hn",
            title="Phoenix discussion on HN",
            outlet="example.com via Hacker News",
            source_kind="social",
            published_at=datetime.now(UTC),
        )
    ])

    persist_mock = AsyncMock(return_value=2)
    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
        patch("tenjin.pipeline.search_fetch.persist_items", persist_mock),
    ):
        await fetch_for_query("phoenix shooting")

    google.search.assert_awaited_once_with("phoenix shooting")
    hn.search.assert_awaited_once_with("phoenix shooting")
    # persist_items called once with both items (combined)
    assert persist_mock.await_count == 1
    items_arg = persist_mock.await_args.args[1]
    assert len(items_arg) == 2


async def test_one_adapter_failure_other_still_persists(fake_redis, fake_search_adapters):
    """If one adapter raises, the other's results still flow through persist_items."""
    google, hn = fake_search_adapters
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)
    fake_redis.delete = AsyncMock(return_value=1)
    google.search = AsyncMock(side_effect=Exception("google down"))
    hn.search = AsyncMock(return_value=[
        RawItem(
            url="https://example.com/hn-only",
            title="Surviving item",
            outlet="example.com via Hacker News",
            source_kind="social",
            published_at=datetime.now(UTC),
        )
    ])

    persist_mock = AsyncMock(return_value=1)
    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
        patch("tenjin.pipeline.search_fetch.persist_items", persist_mock),
    ):
        await fetch_for_query("phoenix shooting")

    items_arg = persist_mock.await_args.args[1]
    assert len(items_arg) == 1
    assert items_arg[0].url == "https://example.com/hn-only"


async def test_redis_unreachable_still_fetches(fake_search_adapters):
    """If Redis raises on every operation, the function still runs adapters."""
    google, hn = fake_search_adapters
    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(side_effect=Exception("redis down"))
    fake_redis.set = AsyncMock(side_effect=Exception("redis down"))
    fake_redis.delete = AsyncMock(side_effect=Exception("redis down"))
    google.search = AsyncMock(return_value=[
        RawItem(
            url="https://example.com/x",
            title="X",
            outlet="AZCentral",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
    ])
    hn.search = AsyncMock(return_value=[])

    persist_mock = AsyncMock(return_value=1)
    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
        patch("tenjin.pipeline.search_fetch.persist_items", persist_mock),
    ):
        await fetch_for_query("phoenix shooting")

    google.search.assert_awaited_once()
    persist_mock.assert_awaited_once()


async def test_persist_failure_swallowed(fake_redis, fake_search_adapters):
    """If persist_items raises, fetch_for_query must not propagate."""
    google, hn = fake_search_adapters
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)
    google.search = AsyncMock(return_value=[
        RawItem(
            url="https://example.com/x",
            title="X",
            outlet="AZCentral",
            source_kind="wire",
            published_at=datetime.now(UTC),
        )
    ])
    hn.search = AsyncMock(return_value=[])

    persist_mock = AsyncMock(side_effect=Exception("db down"))
    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
        patch("tenjin.pipeline.search_fetch.persist_items", persist_mock),
    ):
        # Must not raise.
        await fetch_for_query("phoenix shooting")

    # Lock is intentionally NOT released on persist failure — it expires
    # naturally via the 10s NX EX, and concurrent callers should back off.
    fake_redis.delete.assert_not_called()


async def test_empty_query_short_circuits(fake_redis, fake_search_adapters):
    """fetch_for_query('') and fetch_for_query('   ') return immediately
    without touching Redis or adapters.
    """
    google, hn = fake_search_adapters
    with (
        patch("tenjin.pipeline.search_fetch.get_redis", return_value=fake_redis),
        patch("tenjin.pipeline.search_fetch.GoogleNewsSearchAdapter", return_value=google),
        patch("tenjin.pipeline.search_fetch.HackerNewsSearchAdapter", return_value=hn),
    ):
        await fetch_for_query("")
        await fetch_for_query("   ")

    fake_redis.get.assert_not_called()
    fake_redis.set.assert_not_called()
    google.search.assert_not_called()
    hn.search.assert_not_called()

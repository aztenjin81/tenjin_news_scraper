from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.rss import _DEFAULT_UA, RssAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "rss"
FEED_URL = "https://www.reddit.com/r/worldnews/.rss"


@pytest.fixture
def mock_feed(httpx_mock: HTTPXMock) -> HTTPXMock:
    httpx_mock.add_response(
        url=FEED_URL,
        content=(FIXTURES / "worldnews.xml").read_bytes(),
        headers={"Content-Type": "application/rss+xml"},
    )
    return httpx_mock


async def test_fetch_returns_items(mock_feed: HTTPXMock) -> None:
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    items = await adapter.fetch()
    assert len(items) == 2


async def test_fetch_sets_outlet(mock_feed: HTTPXMock) -> None:
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    items = await adapter.fetch()
    assert all(item.outlet == "r/worldnews" for item in items)


async def test_fetch_maps_fields(mock_feed: HTTPXMock) -> None:
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    items = await adapter.fetch()
    first = items[0]
    assert "Peace talks" in first.title
    assert first.url == "https://example.com/peace-talks"
    assert first.published_at is not None


async def test_fetch_sends_user_agent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=FEED_URL,
        content=(FIXTURES / "worldnews.xml").read_bytes(),
    )
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    await adapter.fetch()
    request = httpx_mock.get_requests()[0]
    assert request.headers["user-agent"] == _DEFAULT_UA


async def test_fetch_survives_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("timeout"))
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    items = await adapter.fetch()
    assert items == []


async def test_fetch_parses_rfc2822_dates(mock_feed: HTTPXMock) -> None:
    """worldnews.xml uses RFC 2822 (`Wed, 06 May 2026 04:00:00 +0000`)."""
    adapter = RssAdapter(name="reddit-worldnews", feed_url=FEED_URL, outlet="r/worldnews")
    items = await adapter.fetch()
    assert all(item.published_at is not None for item in items)
    # First item is 2026-05-06 04:00:00 UTC
    assert items[0].published_at.year == 2026
    assert items[0].published_at.hour == 4


_ATOM_URL = "https://example.com/atom.xml"


async def test_fetch_parses_iso8601_dates(httpx_mock: HTTPXMock) -> None:
    """Atom feeds use ISO 8601 `<updated>` and `<published>`. The previous
    parser silently returned None for these, leaving published_at NULL and
    forcing the article-list sort to fall back to fetched_at — clustering
    every batch together by scrape time."""
    httpx_mock.add_response(
        url=_ATOM_URL,
        content=(FIXTURES / "iso8601.xml").read_bytes(),
        headers={"Content-Type": "application/atom+xml"},
    )
    adapter = RssAdapter(name="atom-test", feed_url=_ATOM_URL, outlet="Atom Feed")
    items = await adapter.fetch()
    assert len(items) == 2
    # Both items must have a parsed published_at — that's the whole regression.
    assert all(item.published_at is not None for item in items), (
        f"NULL pub dates: {[(i.title, i.published_at) for i in items]}"
    )
    # Verify the actual values to make sure we're parsing into UTC correctly.
    by_url = {i.url: i for i in items}
    atom1 = by_url["https://example.com/atom-1"]
    atom2 = by_url["https://example.com/atom-2"]
    assert atom1.published_at.year == 2026
    assert atom1.published_at.hour == 8  # uses <updated>
    assert atom2.published_at.hour == 7  # uses <published>
    assert atom2.published_at.minute == 30


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

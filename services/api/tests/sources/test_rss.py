from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.rss import RssAdapter, _DEFAULT_UA

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

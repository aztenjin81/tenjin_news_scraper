import urllib.parse
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.google_news import GoogleNewsSearchAdapter, _DEFAULT_UA

FIXTURES = Path(__file__).parent / "fixtures" / "google_news"


def _expected_url(q: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
    )


@pytest.fixture
def mock_arizona(httpx_mock: HTTPXMock) -> HTTPXMock:
    httpx_mock.add_response(
        url=_expected_url("shooting arizona"),
        content=(FIXTURES / "search_arizona.xml").read_bytes(),
        headers={"Content-Type": "application/rss+xml"},
    )
    return httpx_mock


async def test_search_returns_items(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert len(items) == 3


async def test_search_extracts_per_entry_outlet(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    outlets = {i.outlet for i in items}
    assert "AZCentral" in outlets
    assert "Reuters" in outlets
    assert "The Arizona Republic" in outlets


async def test_search_strips_outlet_suffix_from_title(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    titles = [i.title for i in items]
    assert any(t == "Three injured in Phoenix mall shooting, suspect at large" for t in titles)
    assert all(" - AZCentral" not in t for t in titles)
    assert all(" - Reuters" not in t for t in titles)
    assert all(" - The Arizona Republic" not in t for t in titles)


async def test_search_sets_source_kind_wire(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert all(i.source_kind == "wire" for i in items)


async def test_search_parses_pubdates(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert all(i.published_at is not None for i in items)
    # Pin a specific value so a timezone-handling bug surfaces immediately.
    # First fixture entry is "Tue, 06 May 2026 18:42:00 GMT".
    first = next(i for i in items if i.title.startswith("Three injured"))
    assert first.published_at.year == 2026
    assert first.published_at.month == 5
    assert first.published_at.day == 6
    assert first.published_at.hour == 18
    assert first.published_at.minute == 42


async def test_search_empty_query_returns_empty_no_request(httpx_mock: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    assert await adapter.search("") == []
    assert await adapter.search("   ") == []
    assert httpx_mock.get_requests() == []


async def test_search_survives_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("connection refused"))
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert items == []


async def test_search_quotes_unicode(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_expected_url("México elecciones"),
        content=(FIXTURES / "search_arizona.xml").read_bytes(),
    )
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("México elecciones")
    assert len(items) == 3


async def test_search_returns_empty_on_http_error(httpx_mock: HTTPXMock) -> None:
    """Google occasionally returns 429/503 under load. The adapter must catch
    raise_for_status() and return [] cleanly.
    """
    httpx_mock.add_response(
        url=_expected_url("rate limited"),
        status_code=429,
    )
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("rate limited")
    assert items == []


async def test_search_sends_user_agent(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    await adapter.search("shooting arizona")
    request = mock_arizona.get_requests()[0]
    assert request.headers["user-agent"] == _DEFAULT_UA


async def test_search_falls_back_when_source_element_missing(httpx_mock: HTTPXMock) -> None:
    """Google occasionally omits the per-item <source> element. Outlet then
    falls back to the flat 'Google News' label.
    """
    no_source_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>An item without a source element</title>
      <link>https://news.google.com/rss/articles/CBMiNX</link>
      <pubDate>Tue, 06 May 2026 18:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
    httpx_mock.add_response(
        url=_expected_url("orphan"),
        content=no_source_xml,
        headers={"Content-Type": "application/rss+xml"},
    )
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("orphan")
    assert len(items) == 1
    assert items[0].outlet == "Google News"
    # Title is unchanged because there's no " - <outlet>" suffix to strip.
    assert items[0].title == "An item without a source element"

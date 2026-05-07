import json
import urllib.parse
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.hackernews import HackerNewsSearchAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "hn_algolia"


def _expected_url(q: str) -> str:
    return (
        "https://hn.algolia.com/api/v1/search?"
        f"query={urllib.parse.quote_plus(q)}&tags=story&hitsPerPage=50"
    )


@pytest.fixture
def mock_rust(httpx_mock: HTTPXMock) -> HTTPXMock:
    httpx_mock.add_response(
        url=_expected_url("rust"),
        json=json.loads((FIXTURES / "search_rust.json").read_text()),
    )
    return httpx_mock


async def test_search_returns_items_with_urls(mock_rust: HTTPXMock) -> None:
    """The fixture has 4 hits — but one is an Ask HN with url=null. Skip it."""
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert len(items) == 3
    assert all(i.url for i in items)


async def test_search_skips_items_without_url(mock_rust: HTTPXMock) -> None:
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    titles = [i.title for i in items]
    assert not any(t.startswith("Ask HN:") for t in titles)


async def test_search_outlet_is_publisher_via_hn(mock_rust: HTTPXMock) -> None:
    """outlet should be '<publisher domain> via Hacker News' — not flat 'HN'."""
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    outlets = {i.outlet for i in items}
    assert "blog.rust-lang.org via Hacker News" in outlets
    assert "open.nytimes.com via Hacker News" in outlets
    assert "example.com via Hacker News" in outlets


async def test_search_sets_source_kind_social(mock_rust: HTTPXMock) -> None:
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert all(i.source_kind == "social" for i in items)


async def test_search_parses_iso8601_dates(mock_rust: HTTPXMock) -> None:
    """Pin specific values so a timezone-handling bug surfaces immediately."""
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert all(i.published_at is not None for i in items)
    by_url = {i.url: i for i in items}
    rust_post = by_url["https://blog.rust-lang.org/2026/05/01/Rust-1.85.html"]
    assert rust_post.published_at.year == 2026
    assert rust_post.published_at.month == 5
    assert rust_post.published_at.day == 1
    assert rust_post.published_at.hour == 16
    assert rust_post.published_at.minute == 0


async def test_search_empty_query_short_circuits(httpx_mock: HTTPXMock) -> None:
    adapter = HackerNewsSearchAdapter()
    assert await adapter.search("") == []
    assert await adapter.search("   ") == []
    assert httpx_mock.get_requests() == []


async def test_search_survives_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("timeout"))
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert items == []


async def test_search_returns_empty_on_http_error(httpx_mock: HTTPXMock) -> None:
    """HN Algolia occasionally returns 503 under load. The adapter must catch
    raise_for_status() and return [] cleanly.
    """
    httpx_mock.add_response(
        url=_expected_url("flaky"),
        status_code=503,
    )
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("flaky")
    assert items == []


async def test_search_extra_fields_populated(mock_rust: HTTPXMock) -> None:
    """Author and extra (score, comments) come through unchanged."""
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    rust_post = next(
        i for i in items if i.url == "https://blog.rust-lang.org/2026/05/01/Rust-1.85.html"
    )
    assert rust_post.author == "steveklabnik"
    assert rust_post.extra is not None
    assert rust_post.extra.get("score") == 842
    assert rust_post.extra.get("comments") == 312


async def test_search_host_fallback_for_malformed_url(httpx_mock: HTTPXMock) -> None:
    """If a URL is non-empty but has no netloc (malformed), the outlet falls
    back to a flat 'Hacker News' label rather than producing 'via Hacker News'.

    NOTE: This produces the redundant string "Hacker News via Hacker News" —
    that is the current behaviour and is documented here, not fixed.  A
    follow-up should special-case the fallback so it emits a cleaner label
    (e.g. "Hacker News" without the suffix, or "unknown via Hacker News").
    """
    httpx_mock.add_response(
        url=_expected_url("malformed"),
        json={
            "hits": [
                {
                    "objectID": "999",
                    "title": "Story with a malformed URL",
                    "url": "not-a-url",
                    "author": "ghost",
                    "points": 1,
                    "num_comments": 0,
                    "created_at": "2026-05-01T16:00:00.000Z",
                    "_tags": ["story"],
                }
            ],
            "nbHits": 1,
        },
    )
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("malformed")
    assert len(items) == 1
    assert items[0].outlet == "Hacker News via Hacker News"

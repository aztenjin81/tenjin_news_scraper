import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.hackernews import HackerNewsAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "hackernews"


@pytest.fixture
def mock_hn(httpx_mock: HTTPXMock) -> HTTPXMock:
    httpx_mock.add_response(
        url="https://hacker-news.firebaseio.com/v0/topstories.json",
        json=json.loads((FIXTURES / "topstories.json").read_text()),
    )
    for name in ("item_1001", "item_1002", "item_1003"):
        httpx_mock.add_response(
            url=f"https://hacker-news.firebaseio.com/v0/item/{name.split('_')[1]}.json",
            json=json.loads((FIXTURES / f"{name}.json").read_text()),
        )
    return httpx_mock


async def test_fetch_returns_stories(mock_hn: HTTPXMock) -> None:
    adapter = HackerNewsAdapter(limit=3)
    items = await adapter.fetch()
    assert len(items) >= 1


async def test_fetch_filters_non_stories(mock_hn: HTTPXMock) -> None:
    adapter = HackerNewsAdapter(limit=3)
    items = await adapter.fetch()
    # item_1003 is a comment — must be excluded
    assert all(item.outlet == "Hacker News" for item in items)
    assert not any("comment" in item.title.lower() for item in items)


async def test_fetch_story_with_url(mock_hn: HTTPXMock) -> None:
    adapter = HackerNewsAdapter(limit=3)
    items = await adapter.fetch()
    story = next(i for i in items if "Hacker News still works" in i.title)
    assert story.url == "https://example.com/hn-still-works"
    assert story.author == "pg"
    assert story.published_at is not None
    assert story.extra["score"] == 342


async def test_fetch_ask_hn_falls_back_to_hn_url(mock_hn: HTTPXMock) -> None:
    adapter = HackerNewsAdapter(limit=3)
    items = await adapter.fetch()
    # item_1002 has no url field — should fall back to HN item URL
    ask = next((i for i in items if "Ask HN" in i.title), None)
    assert ask is not None
    assert ask.url == "https://news.ycombinator.com/item?id=1002"


async def test_fetch_survives_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("connection refused"))
    adapter = HackerNewsAdapter(limit=3)
    items = await adapter.fetch()
    assert items == []

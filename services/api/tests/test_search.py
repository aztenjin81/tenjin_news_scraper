"""Search via the /articles?q= endpoint.

Skipped when Postgres isn't reachable. CI provides a service container.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from tenjin.api.app import app
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
async def _seeded_db():
    if not await _db_reachable():
        pytest.skip("Postgres not reachable")
    await install_topics()
    presets.install()

    async with SessionLocal() as session:
        await session.execute(delete(TopicMatch))
        await session.execute(delete(Article))
        await session.commit()

    now = datetime.now(UTC)
    items = [
        RawItem(
            url="https://example.com/arizona-shooting",
            title="Shooting at Phoenix mall leaves three injured, suspect at large",
            outlet="AP",
            source_kind="wire",
            published_at=now,
            body="The shooting unfolded during the lunch rush near a food court in Arizona.",
        ),
        RawItem(
            url="https://example.com/arizona-water",
            title="Arizona water restrictions extended through summer 2026",
            outlet="Arizona Republic",
            source_kind="regional",
            published_at=now - timedelta(minutes=20),
            body="The state's Department of Water Resources announced new restrictions.",
        ),
        RawItem(
            url="https://example.com/colorado-snow",
            title="Heavy snow blankets Colorado ski resorts",
            outlet="Denver Post",
            source_kind="regional",
            published_at=now - timedelta(minutes=40),
        ),
    ]
    async with SessionLocal() as session:
        await persist_items(session, items)

    yield

    async with SessionLocal() as session:
        await session.execute(delete(TopicMatch))
        await session.execute(delete(Article))
        await session.commit()


def test_search_finds_match_in_title():
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "shooting"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert "Phoenix mall" in body[0]["title"]


def test_search_multi_term_is_AND_not_OR():
    """'arizona shooting' must match the shooting story (both words present)
    but not the water-restrictions story (only 'arizona' present)."""
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "arizona shooting"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert "Phoenix mall" in body[0]["title"]


def test_search_matches_against_snippet_too():
    """The Phoenix story has 'arizona' only in the body; verify snippet match works."""
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "lunch rush"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1


def test_search_is_case_insensitive():
    with TestClient(app) as client:
        r1 = client.get("/articles", params={"q": "ARIZONA"})
        r2 = client.get("/articles", params={"q": "arizona"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert {a["id"] for a in r1.json()} == {a["id"] for a in r2.json()}


def test_search_short_tokens_are_dropped():
    """A search of just 'a' would otherwise match nearly everything."""
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "a"})
        # No tokens >= 2 chars survive parsing, so nothing returned.
        assert r.status_code == 200
        assert r.json() == []


def test_search_no_results_returns_empty_list():
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "antarctica penguins"})
        assert r.status_code == 200
        assert r.json() == []


def test_search_orders_by_recency():
    """Two arizona stories — the one with the newer published_at sorts first."""
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "arizona"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        assert "Phoenix mall" in body[0]["title"]  # newer
        assert "water restrictions" in body[1]["title"]  # older


def test_search_combines_with_topic_filter():
    """When both topic and q are present they should AND together."""
    # No fixture topic matches "Phoenix mall" so this should be empty.
    with TestClient(app) as client:
        r = client.get("/articles", params={"q": "shooting", "topic": "iran-us"})
        assert r.status_code == 200
        assert r.json() == []

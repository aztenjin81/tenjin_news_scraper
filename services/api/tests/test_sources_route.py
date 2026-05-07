"""Tests for the /sources endpoint. DB-free — compute_feed_health is mocked."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tenjin.api.app import create_app
from tenjin.pipeline.health import FeedHealth, FeedHealthReport


@pytest.fixture
def report():
    return FeedHealthReport(
        summary={"total": 2, "ok": 1, "lagging": 0, "silent": 1},
        feeds=[
            FeedHealth(
                name="alpha",
                label="Alpha",
                kind="wire",
                cadence="fast",
                last_item_at=None,
                items_24h=0,
                status="silent",
            ),
            FeedHealth(
                name="beta",
                label="Beta",
                kind="wire",
                cadence="fast",
                last_item_at=datetime.now(UTC) - timedelta(minutes=5),
                items_24h=12,
                status="ok",
            ),
        ],
        generated_at=datetime.now(UTC),
    )


def test_sources_endpoint_shape(report):
    from tenjin.api.routes import sources as routes_mod

    routes_mod._cache_clear()

    app = create_app()
    with patch(
        "tenjin.api.routes.sources.compute_feed_health",
        new=AsyncMock(return_value=report),
    ):
        client = TestClient(app)
        resp = client.get("/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == {"total": 2, "ok": 1, "lagging": 0, "silent": 1}
    assert len(data["feeds"]) == 2
    f0 = data["feeds"][0]
    assert set(f0.keys()) == {
        "name",
        "label",
        "kind",
        "cadence",
        "last_item_at",
        "items_24h",
        "status",
    }


def test_sources_endpoint_caches(report):
    from tenjin.api.routes import sources as routes_mod

    routes_mod._cache_clear()

    mock_compute = AsyncMock(return_value=report)
    app = create_app()
    with patch("tenjin.api.routes.sources.compute_feed_health", new=mock_compute):
        client = TestClient(app)
        client.get("/sources")
        client.get("/sources")
    assert mock_compute.call_count == 1

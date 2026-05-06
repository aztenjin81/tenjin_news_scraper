from fastapi.testclient import TestClient

from tenjin.api.app import app


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_topic_presets_install() -> None:
    from tenjin.topics import presets, registry

    presets.install()
    assert registry.get("iran-us") is not None
    assert registry.get("houthis-red-sea") is not None


def test_canonical_url_strips_tracking() -> None:
    from tenjin.pipeline.normalize import canonical_url

    url = "https://example.com/story?id=42&utm_source=twitter&utm_campaign=x"
    assert canonical_url(url) == "https://example.com/story?id=42"

"""Regression tests for tenjin.config — env var parsing edge cases."""

import importlib

import tenjin.config


def _reload(env_value: str | None, monkeypatch):
    if env_value is None:
        monkeypatch.delenv("API_CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("API_CORS_ORIGINS", env_value)
    importlib.reload(tenjin.config)
    return tenjin.config.Settings()


def test_cors_default(monkeypatch):
    s = _reload(None, monkeypatch)
    assert s.api_cors_origins == ["http://localhost:3000"]


def test_cors_single_string(monkeypatch):
    """Plain string from .env — the case that caused the prod outage."""
    s = _reload("http://localhost:3000", monkeypatch)
    assert s.api_cors_origins == ["http://localhost:3000"]


def test_cors_comma_separated(monkeypatch):
    s = _reload("http://localhost:3000,https://tenjin.us", monkeypatch)
    assert s.api_cors_origins == ["http://localhost:3000", "https://tenjin.us"]


def test_cors_json(monkeypatch):
    s = _reload('["http://localhost:3000","https://tenjin.us"]', monkeypatch)
    assert s.api_cors_origins == ["http://localhost:3000", "https://tenjin.us"]


def test_cors_empty(monkeypatch):
    s = _reload("", monkeypatch)
    assert s.api_cors_origins == []


def test_cors_whitespace_around_entries(monkeypatch):
    s = _reload("http://a.com  ,  http://b.com", monkeypatch)
    assert s.api_cors_origins == ["http://a.com", "http://b.com"]

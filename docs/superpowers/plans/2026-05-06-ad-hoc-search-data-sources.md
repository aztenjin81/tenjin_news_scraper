# Ad-hoc Search Data Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add query-aware sources to ad-hoc search and broaden the always-on scrape with US national/wire outlets, so a search like "shooting in arizona" returns substantive results from publishers we do not individually curate.

**Architecture:** Three sequential PRs. **A**) Add 7 US national/wire feeds to `feeds.py`. **B**) New `SearchAdapter` Protocol + `GoogleNewsSearchAdapter` + `HackerNewsSearchAdapter` — pure adapter infra, not yet wired into the route. **C**) `pipeline/search_fetch.py` with Redis cache (5 min) + lock (10s expiry); `/articles` route awaits the live fetch when `q` is present, swallowing all augmentation failures. Cold queries return in 1–3 s, warm queries (cache hit) return in <100 ms. The existing post-commit publish from PR #27 fans out matched articles via SSE for free.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, asyncpg, Redis (`redis.asyncio`), httpx, feedparser, pytest, `pytest-httpx`, `pytest-asyncio`.

**Source spec:** `docs/superpowers/specs/2026-05-06-ad-hoc-search-data-sources-design.md`

---

## File Structure

### PR A — Background coverage expansion
- **Modify:** `services/api/tenjin/sources/feeds.py` (append 7 entries)
- **Validates against:** `services/api/tests/sources/test_feeds.py` (existing structural smoke tests)

### PR B — Search adapter protocol and adapters
- **Modify:** `services/api/tenjin/sources/base.py` (add `SearchAdapter` Protocol)
- **Create:** `services/api/tenjin/sources/google_news.py`
- **Modify:** `services/api/tenjin/sources/hackernews.py` (add `HackerNewsSearchAdapter`)
- **Create fixtures:**
  - `services/api/tests/sources/fixtures/google_news/search_arizona.xml`
  - `services/api/tests/sources/fixtures/hn_algolia/search_rust.json`
- **Create tests:**
  - `services/api/tests/sources/test_google_news.py`
  - `services/api/tests/sources/test_hackernews_search.py`

### PR C — Search-time fetch and route integration
- **Create:** `services/api/tenjin/pipeline/search_fetch.py`
- **Modify:** `services/api/tenjin/api/routes/articles.py` (await `fetch_for_query` when `q` is present)
- **Create:** `services/api/tests/pipeline/__init__.py`
- **Create:** `services/api/tests/pipeline/test_search_fetch.py`
- **Modify:** `services/api/tests/test_search.py` (one integration test asserting the route triggers the fetch)

---

## Conventions to follow (from `services/api/CLAUDE.md`)

- **Async** by default for I/O. Use `httpx.AsyncClient`.
- **Adapters must not raise.** Log via `structlog` and return `[]`.
- **Routes are thin.** Push logic into `pipeline/`.
- **Schemas vs models.** Never return ORM objects.
- **Settings.** All env access through `tenjin.config.Settings`.

## Conventions to follow (from root `CLAUDE.md`)

- **Branches:** `claude/<short-description>`. Never commit to `main`.
- **Commits:** imperative, scoped subject (`api: add rss adapter`, `api: wire search_fetch into /articles`).
- **PRs:** small and focused. One concern per PR. This plan deliberately produces three.

---

# PR A — Background coverage expansion

Branch: `claude/api-feeds-us-national-wire`. Off `main`.

### Task A1: Add 7 US national / wire feeds

**Files:**
- Modify: `services/api/tenjin/sources/feeds.py`

- [ ] **Step 1: Verify candidate URLs are live.**

For each of the seven candidate feeds below, run a one-off curl from a developer shell (NOT in CI) and confirm: HTTP 200, `Content-Type` is RSS/Atom, body parses as XML with at least one `<item>` (or Atom `<entry>`).

```bash
for url in \
  "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best" \
  "https://feeds.npr.org/1001/rss.xml" \
  "https://www.pbs.org/newshour/feeds/rss/headlines" \
  "https://feeds.nbcnews.com/nbcnews/public/news" \
  "https://www.cbsnews.com/latest/rss/main" \
  "https://abcnews.go.com/abcnews/topstories" \
  "https://rssfeeds.usatoday.com/usatoday-NewsTopStories"; do
  echo "=== $url ==="
  curl -sSL -A "tenjin-news-bot/1.0" -o /tmp/feed.xml -w "%{http_code}\n" "$url"
  head -c 400 /tmp/feed.xml; echo
done
```

If any URL returns non-200 or non-XML, find the current feed URL on the publisher's site and replace it. Do NOT add a feed that fails to fetch — broken feeds become noise in production logs.

- [ ] **Step 2: Append entries to `feeds.py`.**

Add the following at the end of the existing `_rss(...)` chain in `FEEDS`, in a new `# ── US national mainstream ─────────────────────────────────────────────────` section. Replace any URL whose live verification failed in Step 1.

```python
    # ── US national mainstream ────────────────────────────────────────────────
    _rss(
        "reuters-top-news",
        "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
        "Reuters",
        "wire",
    ),
    _rss(
        "npr-news",
        "https://feeds.npr.org/1001/rss.xml",
        "NPR",
        "wire",
    ),
    _rss(
        "pbs-newshour",
        "https://www.pbs.org/newshour/feeds/rss/headlines",
        "PBS NewsHour",
        "wire",
    ),
    _rss(
        "nbc-news",
        "https://feeds.nbcnews.com/nbcnews/public/news",
        "NBC News",
        "wire",
    ),
    _rss(
        "cbs-news",
        "https://www.cbsnews.com/latest/rss/main",
        "CBS News",
        "wire",
    ),
    _rss(
        "abc-news",
        "https://abcnews.go.com/abcnews/topstories",
        "ABC News",
        "wire",
    ),
    _rss(
        "usa-today",
        "https://rssfeeds.usatoday.com/usatoday-NewsTopStories",
        "USA Today",
        "wire",
    ),
```

- [ ] **Step 3: Run the structural smoke tests.**

```bash
cd services/api
pytest tests/sources/test_feeds.py -v
```

Expected: 3 tests pass (`test_all_feeds_have_unique_names`, `test_all_feeds_emit_known_source_kind`, `test_at_least_one_feed_per_kind`). If a duplicate name fails, fix the name (`reuters-top-news` not `reuters`).

- [ ] **Step 4: Commit.**

```bash
git checkout -b claude/api-feeds-us-national-wire
git add services/api/tenjin/sources/feeds.py
git commit -m "api: add 7 US national/wire feeds (Reuters, NPR, PBS, NBC, CBS, ABC, USA Today)"
git push -u origin claude/api-feeds-us-national-wire
gh pr create --title "api: add 7 US national/wire feeds" \
  --body "Closes the no-mainstream-US gap in feeds.py. Helps both topic pages and ad-hoc search by broadening what the always-on scrape ingests. Each URL was curl-verified to return parseable RSS before commit. Smoke tests in tests/sources/test_feeds.py pass."
```

---

# PR B — Search adapter protocol and adapters

Branch: `claude/api-search-adapters`. Off `main` (independent of PR A).

### Task B1: Add `SearchAdapter` Protocol to `sources/base.py`

**Files:**
- Modify: `services/api/tenjin/sources/base.py`

- [ ] **Step 1: Append the Protocol.**

Append after the existing `SourceAdapter` class:

```python
class SearchAdapter(Protocol):
    """Query-aware source. Called from the API request path with a user query.

    Same RawItem output, same error contract as SourceAdapter (log and return []
    on failure — never raise to the caller).
    """

    name: str

    async def search(self, q: str) -> list[RawItem]: ...
```

- [ ] **Step 2: Verify imports are unchanged.**

```bash
cd services/api
ruff check tenjin/sources/base.py
```

Expected: no lint errors. (`Protocol` is already imported by the existing `SourceAdapter`.)

- [ ] **Step 3: Commit.**

```bash
git checkout -b claude/api-search-adapters
git add services/api/tenjin/sources/base.py
git commit -m "api: add SearchAdapter protocol"
```

### Task B2: Create the Google News fixture

**Files:**
- Create: `services/api/tests/sources/fixtures/google_news/search_arizona.xml`

- [ ] **Step 1: Create the fixture file.**

This is hand-authored to keep tests deterministic. It mirrors Google News' real RSS shape with two distinct outlets so the per-entry outlet-extraction test has something to assert against. Use UTF-8.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0">
  <channel>
    <title>"shooting arizona" - Google News</title>
    <link>https://news.google.com/search?q=shooting+arizona</link>
    <description>Google News</description>
    <language>en-US</language>
    <item>
      <title>Three injured in Phoenix mall shooting, suspect at large - AZCentral</title>
      <link>https://news.google.com/rss/articles/CBMiTGh0dHBzOi8vd3d3LmF6Y2VudHJhbC5jb20vc3RvcnkvbmV3cy9sb2NhbC9waG9lbml4LzIwMjYvMDUvMDYvbWFsbC1zaG9vdGluZy8?oc=5</link>
      <guid isPermaLink="false">CBMiTGh0dHBzOi8vd3d3LmF6Y2VudHJhbC5jb20vc3RvcnkvbmV3cy9sb2NhbC9waG9lbml4LzIwMjYvMDUvMDYvbWFsbC1zaG9vdGluZy8</guid>
      <pubDate>Tue, 06 May 2026 18:42:00 GMT</pubDate>
      <description>&lt;a href="..."&gt;Three injured in Phoenix mall shooting&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;AZCentral&lt;/font&gt;</description>
      <source url="https://www.azcentral.com">AZCentral</source>
    </item>
    <item>
      <title>Arizona governor responds to Phoenix shooting - The Arizona Republic</title>
      <link>https://news.google.com/rss/articles/CBMiSGh0dHBzOi8vd3d3LmF6Y2VudHJhbC5jb20vc3RvcnkvbmV3cy9wb2xpdGljcy9hcml6b25hLzIwMjYvMDUvMDYvZ292LXJlc3BvbnNlLw?oc=5</link>
      <guid isPermaLink="false">CBMiSGh0dHBzOi8vd3d3LmF6Y2VudHJhbC5jb20vc3RvcnkvbmV3cy9wb2xpdGljcy9hcml6b25hLzIwMjYvMDUvMDYvZ292LXJlc3BvbnNlLw</guid>
      <pubDate>Tue, 06 May 2026 19:15:00 GMT</pubDate>
      <description>Statement from the governor's office.</description>
      <source url="https://www.azcentral.com">The Arizona Republic</source>
    </item>
    <item>
      <title>Phoenix mall shooting: what we know - Reuters</title>
      <link>https://news.google.com/rss/articles/CBMiNGh0dHBzOi8vd3d3LnJldXRlcnMuY29tL3VzL3Bob2VuaXgtbWFsbC1zaG9vdGluZy8?oc=5</link>
      <guid isPermaLink="false">CBMiNGh0dHBzOi8vd3d3LnJldXRlcnMuY29tL3VzL3Bob2VuaXgtbWFsbC1zaG9vdGluZy8</guid>
      <pubDate>Tue, 06 May 2026 19:50:00 GMT</pubDate>
      <description>Wire-style summary.</description>
      <source url="https://www.reuters.com">Reuters</source>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Verify directory layout.**

```bash
ls services/api/tests/sources/fixtures/google_news/
```

Expected: `search_arizona.xml`

### Task B3: Write the Google News adapter test (basic fetch)

**Files:**
- Create: `services/api/tests/sources/test_google_news.py`

- [ ] **Step 1: Write the test file.**

```python
import urllib.parse
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tenjin.sources.google_news import GoogleNewsSearchAdapter

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
    """Google News appends an outlet name per item via <source> — the adapter
    must surface it as the RawItem.outlet so users see 'AZCentral' / 'Reuters',
    not all 'Google News'.
    """
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    outlets = {i.outlet for i in items}
    assert "AZCentral" in outlets
    assert "Reuters" in outlets
    assert "The Arizona Republic" in outlets


async def test_search_strips_outlet_suffix_from_title(mock_arizona: HTTPXMock) -> None:
    """Google News appends ' - <outlet>' to titles. Strip it so the displayed
    title is the article's actual title.
    """
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    titles = [i.title for i in items]
    assert any(t == "Three injured in Phoenix mall shooting, suspect at large" for t in titles)
    assert all(" - AZCentral" not in t for t in titles)
    assert all(" - Reuters" not in t for t in titles)


async def test_search_sets_source_kind_wire(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert all(i.source_kind == "wire" for i in items)


async def test_search_parses_pubdates(mock_arizona: HTTPXMock) -> None:
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert all(i.published_at is not None for i in items)


async def test_search_empty_query_returns_empty_no_request(httpx_mock: HTTPXMock) -> None:
    """Whitespace-only or empty queries must short-circuit without an HTTP call —
    if we hit Google News with an empty q we'd get a junk top-stories list.
    """
    adapter = GoogleNewsSearchAdapter()
    assert await adapter.search("") == []
    assert await adapter.search("   ") == []
    # If any HTTP request was made, pytest-httpx will fail teardown (no mocks set).
    assert httpx_mock.get_requests() == []


async def test_search_survives_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("connection refused"))
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("shooting arizona")
    assert items == []


async def test_search_quotes_unicode(httpx_mock: HTTPXMock) -> None:
    """Queries with spaces and unicode round-trip through URL-encoding."""
    httpx_mock.add_response(
        url=_expected_url("México elecciones"),
        content=(FIXTURES / "search_arizona.xml").read_bytes(),
    )
    adapter = GoogleNewsSearchAdapter()
    items = await adapter.search("México elecciones")
    assert len(items) == 3
```

- [ ] **Step 2: Run tests, expect failure (module does not exist yet).**

```bash
cd services/api
pytest tests/sources/test_google_news.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tenjin.sources.google_news'`.

### Task B4: Implement `GoogleNewsSearchAdapter`

**Files:**
- Create: `services/api/tenjin/sources/google_news.py`

- [ ] **Step 1: Write the adapter.**

Composes the RSS parsing approach from `tenjin/sources/rss.py` rather than inheriting — `RssAdapter` takes a fixed `feed_url` at construction; the search adapter takes the URL per call.

```python
"""Google News query-aware source. Hits the unofficial RSS search endpoint.

URL: https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en

Each item carries:
- A Google News redirect URL in <link> (CBMi-encoded). We use it as-is. Multiple
  queries that surface the same article share the same redirect URL, so the
  existing canonical_url dedup still collapses them — the URL identifies the
  *article* even if it's a Google redirect, not the publisher's URL. Decoding
  to the publisher URL is a follow-up; not v1.
- A <source url="..."> per entry with the actual publisher name. We extract
  this and use it as RawItem.outlet so users see "AZCentral" / "Reuters" /
  etc., not a flat "Google News".
- A title formatted "<actual title> - <outlet>". We strip the trailing
  " - <outlet>" once we know the outlet.
"""

import calendar
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx
import structlog

from tenjin.sources.base import RawItem

log = structlog.get_logger(__name__)

_DEFAULT_UA = "tenjin-news-bot/1.0 (news aggregator; +https://tenjin.us)"
_FALLBACK_OUTLET = "Google News"
_TIMEOUT_SECONDS = 3.0


@dataclass
class GoogleNewsSearchAdapter:
    """Query-aware adapter satisfying SearchAdapter protocol."""

    name: str = "google-news"
    source_kind: str = "wire"
    user_agent: str = _DEFAULT_UA

    async def search(self, q: str) -> list[RawItem]:
        q = q.strip()
        if not q:
            return []

        url = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        )

        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=headers) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            log.warning("google_news.search_failed", q=q, error=str(e))
            return []

        items: list[RawItem] = []
        for entry in parsed.entries:
            outlet = _extract_outlet(entry)
            title = _strip_outlet_suffix(entry.get("title", "").strip(), outlet)
            published = _to_datetime(
                entry.get("published_parsed") or entry.get("updated_parsed")
            )
            link = entry.get("link", "")
            if not link or not title:
                continue
            items.append(
                RawItem(
                    url=link,
                    title=title,
                    outlet=outlet,
                    source_kind=self.source_kind,
                    published_at=published,
                    body=entry.get("summary"),
                )
            )
        return items


def _extract_outlet(entry) -> str:
    """feedparser exposes <source>Outlet Name</source> as entry.source, a
    FeedParserDict whose `title` attribute is the text content. Fall back to
    a flat label if the element is missing.
    """
    source = entry.get("source")
    if source is None:
        return _FALLBACK_OUTLET
    title = source.get("title") if isinstance(source, dict) else getattr(source, "title", None)
    return title.strip() if title else _FALLBACK_OUTLET


def _strip_outlet_suffix(title: str, outlet: str) -> str:
    suffix = f" - {outlet}"
    if title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def _to_datetime(parsed: time.struct_time | None) -> datetime | None:
    """feedparser hands us struct_time in UTC. Convert to aware datetime."""
    if parsed is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
```

- [ ] **Step 2: Run the tests.**

```bash
cd services/api
pytest tests/sources/test_google_news.py -v
```

Expected: all 8 tests pass.

If `test_search_extracts_per_entry_outlet` fails because feedparser nests the source element differently than expected, check `parsed.entries[0]` in a Python REPL with the fixture and adjust `_extract_outlet`. The contract is: surface the per-entry `<source>` element's text as the outlet.

- [ ] **Step 3: Commit.**

```bash
git add services/api/tenjin/sources/google_news.py \
        services/api/tests/sources/fixtures/google_news/search_arizona.xml \
        services/api/tests/sources/test_google_news.py
git commit -m "api: add GoogleNewsSearchAdapter with per-entry outlet extraction"
```

### Task B5: Create the HN Algolia fixture

**Files:**
- Create: `services/api/tests/sources/fixtures/hn_algolia/search_rust.json`

- [ ] **Step 1: Write the fixture.**

Trimmed Algolia response — 4 hits, one of which has no `url` (Ask HN) so the skip path is exercised. Note: `created_at` is ISO 8601 with `.000Z` suffix in the real API.

```json
{
  "hits": [
    {
      "objectID": "39000001",
      "title": "Rust 1.85 released",
      "url": "https://blog.rust-lang.org/2026/05/01/Rust-1.85.html",
      "author": "steveklabnik",
      "points": 842,
      "num_comments": 312,
      "created_at": "2026-05-01T16:00:00.000Z",
      "_tags": ["story", "author_steveklabnik", "story_39000001"]
    },
    {
      "objectID": "39000002",
      "title": "Why Rust's borrow checker is the best thing since sliced bread",
      "url": "https://example.com/rust-borrow-checker",
      "author": "ferrous_systems",
      "points": 412,
      "num_comments": 158,
      "created_at": "2026-04-29T09:30:00.000Z",
      "_tags": ["story", "author_ferrous_systems"]
    },
    {
      "objectID": "39000003",
      "title": "Ask HN: Best resources to learn Rust in 2026?",
      "url": null,
      "author": "newbie42",
      "points": 95,
      "num_comments": 187,
      "created_at": "2026-04-28T22:14:00.000Z",
      "_tags": ["story", "ask_hn", "author_newbie42"]
    },
    {
      "objectID": "39000004",
      "title": "Rust adoption at NYTimes engineering",
      "url": "https://open.nytimes.com/rust-adoption-2026",
      "author": "nyt_eng",
      "points": 287,
      "num_comments": 94,
      "created_at": "2026-04-27T13:00:00.000Z",
      "_tags": ["story", "author_nyt_eng"]
    }
  ],
  "nbHits": 4,
  "page": 0,
  "nbPages": 1,
  "hitsPerPage": 50,
  "query": "rust"
}
```

### Task B6: Write the HN search adapter test

**Files:**
- Create: `services/api/tests/sources/test_hackernews_search.py`

- [ ] **Step 1: Write the test file.**

```python
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
    """Items with no external URL (Ask HN, etc.) shouldn't make it through —
    they'd point at HN's internal item page, which is noise for our search.
    """
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


async def test_search_sets_source_kind_social(mock_rust: HTTPXMock) -> None:
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert all(i.source_kind == "social" for i in items)


async def test_search_parses_iso8601_dates(mock_rust: HTTPXMock) -> None:
    adapter = HackerNewsSearchAdapter()
    items = await adapter.search("rust")
    assert all(i.published_at is not None for i in items)
    # First fixture hit is 2026-05-01T16:00Z
    by_url = {i.url: i for i in items}
    rust_post = by_url["https://blog.rust-lang.org/2026/05/01/Rust-1.85.html"]
    assert rust_post.published_at.year == 2026
    assert rust_post.published_at.month == 5


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
```

- [ ] **Step 2: Run tests, expect failure (`HackerNewsSearchAdapter` does not exist).**

```bash
cd services/api
pytest tests/sources/test_hackernews_search.py -v
```

Expected: FAIL — `ImportError: cannot import name 'HackerNewsSearchAdapter'`.

### Task B7: Implement `HackerNewsSearchAdapter`

**Files:**
- Modify: `services/api/tenjin/sources/hackernews.py`

- [ ] **Step 1: Append the new class to `hackernews.py`.**

Add at the end of the existing file. Reuses the file because it lives in the same source family.

```python
import urllib.parse
from urllib.parse import urlparse

_ALGOLIA = "https://hn.algolia.com/api/v1/search"
_ALGOLIA_TIMEOUT = 3.0


@dataclass
class HackerNewsSearchAdapter:
    """Query-aware HN adapter using the public Algolia search endpoint.

    No auth required, well-documented, free. Returns story-tagged hits only.
    The outlet is the publisher's domain prefixed with 'via Hacker News' so
    users understand HN was the discovery channel, not the publisher.
    """

    name: str = "hackernews-search"
    source_kind: str = "social"

    async def search(self, q: str) -> list[RawItem]:
        q = q.strip()
        if not q:
            return []

        url = (
            f"{_ALGOLIA}?query={urllib.parse.quote_plus(q)}"
            "&tags=story&hitsPerPage=50"
        )

        try:
            async with httpx.AsyncClient(timeout=_ALGOLIA_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning("hackernews_search.failed", q=q, error=str(e))
            return []

        items: list[RawItem] = []
        for hit in data.get("hits", []):
            link = hit.get("url")
            if not link:
                # Ask HN / Show HN with no external link — skip; we don't want
                # results that point at HN's internal item pages.
                continue
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            host = urlparse(link).netloc.lower() or "Hacker News"
            outlet = f"{host} via Hacker News"
            published = _parse_algolia_date(hit.get("created_at"))
            items.append(
                RawItem(
                    url=link,
                    title=title,
                    outlet=outlet,
                    source_kind=self.source_kind,
                    author=hit.get("by") or hit.get("author"),
                    published_at=published,
                    extra={
                        "score": hit.get("points"),
                        "comments": hit.get("num_comments", 0),
                    },
                )
            )
        return items


def _parse_algolia_date(raw: str | None) -> datetime | None:
    """Algolia uses ISO 8601 with millisecond suffix, e.g. '2026-05-01T16:00:00.000Z'."""
    if not raw:
        return None
    try:
        # Python's fromisoformat (3.11+) accepts 'Z' suffix.
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
```

- [ ] **Step 2: Run the tests.**

```bash
cd services/api
pytest tests/sources/test_hackernews_search.py -v
pytest tests/sources/test_hackernews.py -v  # existing tests must still pass
```

Expected: all new tests pass; the 5 existing `test_hackernews.py` tests still pass.

- [ ] **Step 3: Commit.**

```bash
git add services/api/tenjin/sources/hackernews.py \
        services/api/tests/sources/fixtures/hn_algolia/search_rust.json \
        services/api/tests/sources/test_hackernews_search.py
git commit -m "api: add HackerNewsSearchAdapter via Algolia search API"
```

- [ ] **Step 4: Push and open PR.**

```bash
git push -u origin claude/api-search-adapters
gh pr create --title "api: add SearchAdapter protocol + Google News + HN Algolia adapters" \
  --body "Adds the query-aware adapter pattern that PR C will wire into the search route. No production code paths reach these yet — pure infra. Each adapter follows the existing log-and-return-[] error convention."
```

---

# PR C — Search-time fetch and route integration

Branch: `claude/api-search-fetch-integration`. Off `main`. Depends on PR B being merged.

### Task C1: Create the test package init

**Files:**
- Create: `services/api/tests/pipeline/__init__.py`

- [ ] **Step 1: Create empty init file.**

```bash
mkdir -p services/api/tests/pipeline
touch services/api/tests/pipeline/__init__.py
```

The existing top-level `tests/__init__.py` exists; pytest discovers nested packages automatically when they have an init file.

### Task C2: Write the `fetch_for_query` test for cache-hit short-circuit

**Files:**
- Create: `services/api/tests/pipeline/test_search_fetch.py`

- [ ] **Step 1: Write the initial test.**

```python
"""Tests for pipeline.search_fetch.fetch_for_query.

The function is best-effort: it must never raise to the caller. Failures of
the cache, the lock, the adapters, or persistence all degrade silently —
search itself uses the DB regardless.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tenjin.pipeline.search_fetch import fetch_for_query


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
    fake_redis.get = AsyncMock(return_value="1")  # cache hit (any truthy value)

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
```

- [ ] **Step 2: Run, expect failure.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tenjin.pipeline.search_fetch'`.

### Task C3: Implement `fetch_for_query` — cache-hit path only

**Files:**
- Create: `services/api/tenjin/pipeline/search_fetch.py`

- [ ] **Step 1: Write the minimal module.**

```python
"""Search-time augmentation: hit query-aware sources, persist results.

Best-effort. Any failure (cache, lock, adapters, persistence) is logged and
swallowed. Search itself returns DB results regardless.
"""

import asyncio
import hashlib

import structlog

from tenjin.db.redis import get_redis
from tenjin.db.session import SessionLocal
from tenjin.pipeline.persist import persist_items
from tenjin.sources.base import RawItem
from tenjin.sources.google_news import GoogleNewsSearchAdapter
from tenjin.sources.hackernews import HackerNewsSearchAdapter

log = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 300   # 5 min
_LOCK_TTL_SECONDS = 10
_ADAPTER_TIMEOUT_SECONDS = 3.0  # belt + suspenders; adapters have their own timeout


def _cache_key(q: str) -> str:
    norm = q.lower().strip().encode()
    return f"search:q:{hashlib.sha256(norm).hexdigest()[:16]}"


def _lock_key(q: str) -> str:
    norm = q.lower().strip().encode()
    return f"search:lock:{hashlib.sha256(norm).hexdigest()[:16]}"


async def fetch_for_query(q: str) -> None:
    """Best-effort: hit query-aware sources for q, persist new articles.

    Uses Redis to cache the fact that we recently fetched this query (5 min)
    and a Redis lock to prevent thundering herd. If Redis is unreachable, runs
    the fetch unconditionally — degraded but functional.
    """
    if not q.strip():
        return

    try:
        redis = get_redis()
        cached = await redis.get(_cache_key(q))
        if cached:
            return
    except Exception as e:
        log.warning("search_fetch.cache_check_failed", q=q, error=str(e))
        # Fall through and fetch anyway.
```

- [ ] **Step 2: Run the test.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py::test_cache_hit_skips_fetch -v
```

Expected: PASS.

### Task C4: Test for lock contention

**Files:**
- Modify: `services/api/tests/pipeline/test_search_fetch.py`

- [ ] **Step 1: Add the test.**

Append to the existing test file:

```python
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
```

- [ ] **Step 2: Run, expect failure.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py::test_lock_contention_skips_fetch -v
```

Expected: FAIL — the current implementation returns early after the cache check; it doesn't try to acquire a lock yet.

### Task C5: Implement Redis lock acquisition

**Files:**
- Modify: `services/api/tenjin/pipeline/search_fetch.py`

- [ ] **Step 1: Extend `fetch_for_query` to acquire a lock and short-circuit on contention.**

Replace the function body with:

```python
async def fetch_for_query(q: str) -> None:
    """Best-effort: hit query-aware sources for q, persist new articles."""
    if not q.strip():
        return

    redis_available = True
    try:
        redis = get_redis()
        if await redis.get(_cache_key(q)):
            return
        # NX = only set if absent. EX = expiry seconds. Returns truthy on acquire.
        acquired = await redis.set(_lock_key(q), "1", nx=True, ex=_LOCK_TTL_SECONDS)
        if not acquired:
            return
    except Exception as e:
        log.warning("search_fetch.redis_unavailable", q=q, error=str(e))
        redis_available = False

    # Fetch and persist will go here in Task C7.
    _ = redis_available  # keep ref for next task
```

- [ ] **Step 2: Run the test.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py -v
```

Expected: both `test_cache_hit_skips_fetch` and `test_lock_contention_skips_fetch` pass.

### Task C6: Test for adapter fan-out and persistence

**Files:**
- Modify: `services/api/tests/pipeline/test_search_fetch.py`

- [ ] **Step 1: Add the test.**

```python
from datetime import UTC, datetime

from tenjin.sources.base import RawItem


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
    # Cache was populated.
    fake_redis.set.assert_any_call(_cache_key_match("phoenix shooting"), "1", ex=300)


def _cache_key_match(q: str) -> str:
    """Helper to compute the same cache key as the implementation for assertion."""
    import hashlib
    return f"search:q:{hashlib.sha256(q.lower().strip().encode()).hexdigest()[:16]}"
```

- [ ] **Step 2: Run, expect failure.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py::test_persists_results_from_both_adapters -v
```

Expected: FAIL — adapters are never called by the current implementation.

### Task C7: Implement adapter fan-out and persist

**Files:**
- Modify: `services/api/tenjin/pipeline/search_fetch.py`

- [ ] **Step 1: Replace `fetch_for_query` body with the full version.**

```python
async def fetch_for_query(q: str) -> None:
    """Best-effort: hit query-aware sources for q, persist new articles."""
    if not q.strip():
        return

    try:
        redis = get_redis()
        if await redis.get(_cache_key(q)):
            return
        acquired = await redis.set(_lock_key(q), "1", nx=True, ex=_LOCK_TTL_SECONDS)
        if not acquired:
            return
    except Exception as e:
        log.warning("search_fetch.redis_unavailable", q=q, error=str(e))
        # Continue without cache/lock — degraded but functional.

    try:
        items = await _gather_search_items(q)
        if items:
            async with SessionLocal() as session:
                await persist_items(session, items)
    except Exception as e:
        log.warning("search_fetch.fetch_or_persist_failed", q=q, error=str(e))
        return

    try:
        await get_redis().set(_cache_key(q), "1", ex=_CACHE_TTL_SECONDS)
        await get_redis().delete(_lock_key(q))
    except Exception as e:
        log.warning("search_fetch.cache_set_failed", q=q, error=str(e))


async def _gather_search_items(q: str) -> list[RawItem]:
    google = GoogleNewsSearchAdapter()
    hn = HackerNewsSearchAdapter()
    results = await asyncio.gather(google.search(q), hn.search(q), return_exceptions=True)

    items: list[RawItem] = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("search_fetch.adapter_failed", q=q, error=str(r))
            continue
        items.extend(r)
    return items
```

- [ ] **Step 2: Run the persistence test.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py -v
```

Expected: all three tests pass (cache hit, lock contention, persist).

### Task C8: Test for adapter failure resilience and Redis-down fallback

**Files:**
- Modify: `services/api/tests/pipeline/test_search_fetch.py`

- [ ] **Step 1: Add tests.**

```python
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
    """If Redis raises on every operation, the function still runs adapters
    and tries to persist. Degraded but functional.
    """
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
```

- [ ] **Step 2: Run all `test_search_fetch.py` tests.**

```bash
cd services/api
pytest tests/pipeline/test_search_fetch.py -v
```

Expected: all 6 tests pass. The current implementation already handles these cases (try/except around fetch+persist, redis unavailable bypass), so no impl change needed for this task.

If `test_redis_unreachable_still_fetches` fails, the implementation may be relying on the redis client being reachable for the post-persist cache.set. The pattern is: catch the exception around the cache.set/lock.delete cleanup so the function still returns cleanly. Verify the current `fetch_for_query` matches Task C7's body.

- [ ] **Step 3: Commit `pipeline/search_fetch.py` plus its tests.**

```bash
git checkout -b claude/api-search-fetch-integration
git add services/api/tenjin/pipeline/search_fetch.py \
        services/api/tests/pipeline/__init__.py \
        services/api/tests/pipeline/test_search_fetch.py
git commit -m "api: add pipeline.search_fetch with Redis cache + lock + adapter fan-out"
```

### Task C9: Wire `fetch_for_query` into the `/articles` route

**Files:**
- Modify: `services/api/tenjin/api/routes/articles.py`

- [ ] **Step 1: Add the import and the await.**

Replace the existing `list_articles` body. The change is two lines: an import at the top, and an `await fetch_for_query(q)` inside the `if q:` branch, wrapped in try/except so a failure can never propagate.

At the top of the file, add:

```python
import structlog

from tenjin.pipeline.search_fetch import fetch_for_query

log = structlog.get_logger(__name__)
```

And inside `list_articles`, modify the `if q:` block from this:

```python
    if q:
        terms = _parse_query(q)
        for term in terms:
            ...
        if not terms:
            return []
```

To this (note the new try/except awaiting `fetch_for_query` BEFORE the DB query):

```python
    if q:
        terms = _parse_query(q)
        if not terms:
            return []
        # Best-effort live augmentation. Never propagates — search returns DB
        # results regardless of whether the live fetch ran.
        try:
            await fetch_for_query(q)
        except Exception as e:
            log.warning("articles.search_fetch_failed", q=q, error=str(e))
        for term in terms:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    Article.title.ilike(pattern),
                    Article.snippet.ilike(pattern),
                )
            )
```

The change: (a) we check `if not terms: return []` *before* spending the network call, (b) we await `fetch_for_query(q)` after that early-return guard, (c) the existing term-loop runs unchanged.

- [ ] **Step 2: Run existing search tests.**

```bash
cd services/api
pytest tests/test_search.py -v
```

Expected: all 8 existing tests pass. They run against a real Postgres but mock no live HTTP — `fetch_for_query` will call out to Google News and HN Algolia and probably fail/timeout in CI. That is fine — the route's try/except swallows it and returns DB results.

If any test fails due to network calls, mock `fetch_for_query` in the test fixture by adding an autouse fixture that patches it to a no-op AsyncMock. Sketch:

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def _stub_fetch_for_query():
    with patch("tenjin.api.routes.articles.fetch_for_query", AsyncMock(return_value=None)):
        yield
```

This belongs at the top of `tests/test_search.py` so the existing tests stay focused on DB substring matching, with the live-fetch behavior tested separately.

### Task C10: Integration test — route triggers `fetch_for_query`

**Files:**
- Modify: `services/api/tests/test_search.py`

- [ ] **Step 1: Add the test alongside existing ones.**

```python
async def test_search_with_q_triggers_fetch_for_query():
    """A query with at least one valid term must call fetch_for_query before
    running the DB query. The fetch itself is mocked here — the contract is:
    if q parses to >= 1 term, fetch_for_query is awaited.
    """
    from unittest.mock import AsyncMock, patch

    with patch(
        "tenjin.api.routes.articles.fetch_for_query",
        AsyncMock(return_value=None),
    ) as mock_fetch:
        with TestClient(app) as client:
            client.get("/articles", params={"q": "shooting"})

        mock_fetch.assert_awaited_once_with("shooting")


async def test_search_with_short_query_does_not_call_fetch():
    """A query that parses to zero terms (e.g. just 'a') skips the fetch."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "tenjin.api.routes.articles.fetch_for_query",
        AsyncMock(return_value=None),
    ) as mock_fetch:
        with TestClient(app) as client:
            r = client.get("/articles", params={"q": "a"})
            assert r.json() == []

        mock_fetch.assert_not_called()
```

- [ ] **Step 2: Run the new tests.**

```bash
cd services/api
pytest tests/test_search.py::test_search_with_q_triggers_fetch_for_query tests/test_search.py::test_search_with_short_query_does_not_call_fetch -v
```

Expected: both pass.

- [ ] **Step 3: Run the full test suite for the package.**

```bash
cd services/api
pytest -v
```

Expected: all tests pass. Should be ≥ 50 (8 search + 4 publish + the rest of the suite + the 14 new ones added by this PR).

- [ ] **Step 4: Commit.**

```bash
git add services/api/tenjin/api/routes/articles.py \
        services/api/tests/test_search.py
git commit -m "api: wire search_fetch into /articles when q is present"
```

- [ ] **Step 5: Push and open PR.**

```bash
git push -u origin claude/api-search-fetch-integration
gh pr create --title "api: search-time augmentation via Google News + HN Algolia" \
  --body "$(cat <<'EOF'
Wires the SearchAdapter implementations from PR #B into /articles via a
new pipeline/search_fetch.fetch_for_query, gated by a 5-min Redis cache
and a 10s NX lock to prevent thundering herd.

Cold queries: ~1-3s (gated by 3s adapter timeout). Warm queries (cache
hit): unchanged from current sub-100ms.

All failures degrade gracefully — adapter timeouts, Redis down, persist
failure: search returns DB results regardless.

Topic-matched articles flow through persist_items() and are published to
Redis pubsub by the existing post-commit publish, so an active topic
viewer sees query-time hits in real time via the SSE channel from #27.

Closes the design in docs/superpowers/specs/2026-05-06-ad-hoc-search-data-sources-design.md.
EOF
)"
```

---

## Self-review notes

**Spec coverage:**
- PR A: 7 feeds covered by Task A1
- PR B: SearchAdapter Protocol covered by Task B1; Google News adapter + tests by Tasks B2–B4; HN Algolia adapter + tests by Tasks B5–B7
- PR C: fetch_for_query covered by Tasks C1–C8 (cache hit, lock contention, persist, adapter failure, redis down, persist failure); route integration by Tasks C9–C10

**Type consistency:**
- `SearchAdapter` Protocol method is `search(self, q: str) -> list[RawItem]`. Both adapters implement that signature.
- `fetch_for_query(q: str) -> None`. Same name everywhere it's referenced.
- `_cache_key` / `_lock_key` are module-private and consistent across all impl/test references.

**Known limitations carried forward from spec:**
- Google News URLs are redirect URLs; canonical_url dedup still works because the redirect URL is article-stable, but click-through goes through Google rather than direct to publisher. v1 acceptable; URL unwrapping is a follow-up.
- No live network verification for new feeds in CI — relies on the implementer running curl in Step 1 of Task A1 before commit.

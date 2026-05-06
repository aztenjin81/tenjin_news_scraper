# Ad-hoc search: data sources

Status: design approved 2026-05-06.

## Problem

The ad-hoc search shipped in PR #28 (`/articles?q=…` with ILIKE on title and snippet) is constrained to articles already in the DB. The DB is filled by ~40 curated RSS feeds plus HackerNews and 9 Reddit subs, all of them either topic-bound or general aggregators. There are zero US national mainstream outlets (no Reuters, NPR, NBC, CBS, ABC, USA Today, PBS), no US local papers, no wire services beyond AP, and no query-aware sources at all.

The result: a query like "shooting in arizona" returns few or zero hits even when relevant stories exist on the open web. We need to close two distinct gaps:

- **Coverage gap** — the always-on scrape misses obvious national-tier outlets that any topic page or search ought to surface.
- **Liveness gap** — search needs to reach beyond what we have already ingested, hitting query-aware sources at request time so that long-tail and breaking queries return real results.

## Goals

- A search for any reasonable phrase returns substantive results, not an empty page.
- Long-tail queries (local US, niche events) hit query-aware aggregators so we surface stories from publishers we do not individually scrape.
- Query-time results flow through the same pipeline as scraped articles, so they are deduplicated, topic-matched, and (when applicable) fan out via the SSE pubsub from PR #27.
- No new editorial or LLM logic in v1. No new infra dependencies (no Bing, no NewsAPI).
- Search latency stays sub-100ms on warm queries; cold queries land in 1–3 seconds.

## Non-goals

- Per-query SSE channels. Polling via `SearchStream` (already shipped in PR #28) is enough for v1.
- Specialty verticals (tech, science, business). Defer until query patterns suggest a need.
- Bing News, NewsAPI, GDELT, paid APIs. Defer.
- A query-only article flag with accelerated aging. The existing 30-day prune handles bounded growth.
- Ranking, scoring, or LLM-augmented relevance. Out of scope per the v1 prohibition in the project root CLAUDE.md.

## Architecture

Three independently shippable PRs, in order:

| PR | Concern | Depends on |
|----|---------|------------|
| **A** | Add 6–8 US national / wire feeds to `feeds.py` | Nothing |
| **B** | New `SearchAdapter` protocol; `GoogleNewsSearchAdapter`; `HackerNewsSearchAdapter`; fixtures and tests | Nothing (pure adapter infra, not yet wired) |
| **C** | `pipeline/search_fetch.py` with Redis cache and lock; wire into `/articles` route; integration test | PR B |

Each PR is reviewable on its own. PR A could ship same-day. PRs B and C unlock the live-fetch behavior.

## PR A — Background coverage expansion

Add the following entries to `services/api/tenjin/sources/feeds.py`. All `wire` source kind unless noted; verify URLs and `paywall=` settings against the actual feed before commit.

| Outlet | Feed URL (verify before commit) | Kind | Paywall? |
|--------|---------------------------------|------|----------|
| Reuters | `https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best` | wire | no |
| NPR | `https://feeds.npr.org/1001/rss.xml` | wire | no |
| PBS NewsHour | `https://www.pbs.org/newshour/feeds/rss/headlines` | wire | no |
| NBC News | `https://feeds.nbcnews.com/nbcnews/public/news` | wire | no |
| CBS News | `https://www.cbsnews.com/latest/rss/main` | wire | no |
| ABC News | `https://abcnews.go.com/abcnews/topstories` | wire | no |
| USA Today | `https://rssfeeds.usatoday.com/usatoday-NewsTopStories` | wire | no |

URLs above are reasonable starting candidates; the implementer must `curl` each one and confirm it returns parseable RSS/Atom before adding it. Several outlets retire feed paths without redirecting, which is exactly the failure mode that prompted the BBC and Xinhua removals already documented in `feeds.py` comments.

A smoke test that asserts each new feed parses to at least one item against a captured fixture is sufficient. Live network calls in tests are prohibited.

## PR B — Search adapter protocol and adapters

### `SearchAdapter` protocol

Add to `services/api/tenjin/sources/base.py`:

```python
class SearchAdapter(Protocol):
    name: str

    async def search(self, q: str) -> list[RawItem]: ...
```

`RawItem` is the same type emitted by `SourceAdapter.fetch()`. The contract differs only in invocation: `fetch()` is parameterless and pulls a feed; `search(q)` takes the user's query and returns matching items.

Add a parallel decorator/registry mirroring `SourceAdapter`'s if and only if more than one such adapter needs runtime lookup. For v1 the two adapters are referenced directly from `pipeline/search_fetch.py`, so a registry is unnecessary.

### `GoogleNewsSearchAdapter`

New file: `services/api/tenjin/sources/google_news.py`.

- Endpoint: `https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en`
- Query escaping: `urllib.parse.quote_plus`. Refuse to fetch if `q` is empty or has only whitespace.
- Reuses the RSS parsing helpers from `tenjin/sources/rss.py`. Compose, do not inherit — the existing `RssAdapter` takes a fixed feed URL at construction; the search adapter takes the URL per call.
- Per-entry outlet extraction: each Google News item carries a `<source url="…">Outlet Name</source>` element. Use that as `outlet` rather than a hard-coded "Google News" label, so users see "AZCentral", "Reuters", "AP", and so on. Fall back to "Google News" if the source element is missing.
- `source_kind`: `wire`. Google News aggregates wire-style headlines from many publishers; `wire` is the closest match in our taxonomy.
- HTTP timeout: 3 seconds. On timeout or HTTP error: log and return `[]`. Same convention as scraped feeds per the services/api CLAUDE.md ("Errors from sources are normal").
- User-Agent: `tenjin-news-bot/1.0`, matching `RssAdapter`.

### `HackerNewsSearchAdapter`

Add to existing `services/api/tenjin/sources/hackernews.py`, alongside the current `HackerNewsAdapter`.

- Endpoint: `https://hn.algolia.com/api/v1/search?query={q}&tags=story&hitsPerPage=50`
- JSON response. Each hit has `objectID`, `title`, `url`, `created_at` (ISO 8601), `points`, `num_comments`, `author`.
- Skip hits without a `url` (Algolia returns Ask HN / Show HN posts that have no external link; those are HN-internal and would get a noisy URL).
- `source_kind`: `social`.
- `outlet`: derived from the URL host, prefixed with "via Hacker News" — e.g., a hit linking to `nytimes.com` becomes outlet `nytimes.com via Hacker News`. This matches user expectations: HN is the discovery channel, not the publisher.
- Same 3s timeout, same User-Agent, same error-handling convention.

### Fixtures

- `services/api/tests/sources/fixtures/google_news/search_arizona.xml` — captured RSS response for `q=shooting+in+arizona`. Hand-trim to ~5 items for test stability.
- `services/api/tests/sources/fixtures/hn_algolia/search_rust.json` — captured JSON for `q=rust`. Hand-trim to ~5 hits, keep at least one Ask-HN-style item with no `url` to verify the skip path.

### Tests (PR B)

- Each adapter against its fixture: at least one normalized `RawItem` produced; `outlet` is extracted per-entry for Google News (assert two distinct outlets across the fixture); HN adapter skips items with no `url`.
- ASCII-only URL handling: query with spaces and unicode (e.g., `Cuba`, `México`) round-trips through quoting without raising.
- Empty / whitespace-only query short-circuits to `[]` without making an HTTP call.

## PR C — Search-time fetch and route integration

### `pipeline/search_fetch.py`

```python
async def fetch_for_query(q: str) -> None:
    """
    Best-effort: hit query-aware sources for `q`, persist any new articles.

    Always returns. Failures are logged and swallowed — search must never
    fail because the augmentation failed.
    """
```

Behavior:

1. **Normalize**: `key = sha256(q.lower().strip().encode()).hexdigest()[:16]`. Reusing the route's existing `_parse_query` rules (≥2 chars, ≤8 terms) before hashing is acceptable but not required; the lock and cache are correctness-orthogonal.
2. **Cache check**: `GET search:q:{key}`. If present, return immediately — a recent caller has already populated the DB.
3. **Lock acquire**: `SET search:lock:{key} 1 NX EX 10`. If the SET fails (another worker holds the lock), return immediately. Don't block search on a fetch we don't own.
4. **Fan out**: `asyncio.gather(GoogleNewsSearchAdapter().search(q), HackerNewsSearchAdapter().search(q), return_exceptions=True)`. Each adapter has its own internal 3s timeout (set in PR B); `gather` waits for the slower one.
5. **Pipeline**: collected `RawItem`s flow through `normalize_items → dedupe_items → match_topics → persist_items`. Same call sequence as `workers/scrape.run_all` already uses. Any new articles that match a topic will be published to Redis pubsub by the existing `persist_items` post-commit publish (free SSE delivery).
6. **Cache set**: `SET search:q:{key} 1 EX 300` (5-minute TTL).
7. **Lock release**: best-effort `DEL search:lock:{key}`. The 10s expiry is the real safety net; the explicit DEL is a courtesy.
8. **Errors**: any exception from steps 3–7 is caught at the function boundary, logged with `q`, and swallowed. The search response is unaffected.

If the Redis client raises (Redis unreachable), skip steps 2/3/6/7 entirely and execute the fetch unconditionally. Degraded but functional. Mirrors the post-commit publish convention already in `pipeline/publish.py`.

### Route integration

`services/api/tenjin/api/routes/articles.py`:

- After parsing `q` via existing `_parse_query`, if at least one term remains, call `await fetch_for_query(q)` before the SQL query.
- Wrap in a try/except `Exception` that logs and continues. A failed augmentation must never propagate.
- The existing query construction is unchanged. The DB query simply sees fresh rows when the live fetch persisted any.

This keeps the route handler thin: one new function call. No business logic moves into the route.

### Tests (PR C)

- `test_fetch_for_query_cache_hit` — Redis returns a cached value; assert no adapter was called.
- `test_fetch_for_query_lock_contention` — `SET … NX` returns falsy; assert no adapter was called.
- `test_fetch_for_query_persists_results` — adapters return canned `RawItem`s; after the call, assert articles are in the DB and the topic-match join populated where expected.
- `test_fetch_for_query_adapter_failure` — one adapter raises, the other returns items; assert the surviving items are persisted and the function returns cleanly.
- `test_fetch_for_query_redis_down` — Redis client raises on `SET`; assert the function still fetches and persists.
- `test_articles_q_triggers_fetch` — integration: hit `/articles?q=foo` with mocked adapters; assert (a) `fetch_for_query` ran, (b) the DB query returned the expected rows. Existing 8 search tests in `test_search.py` continue to pass.

## Data flow

### Cold search

```
User types "shooting in arizona"
  /search?q=shooting+in+arizona               (Next.js SSR)
  /api/articles?q=shooting+in+arizona         (same-origin proxy)
  GET /articles?q=shooting+in+arizona         (FastAPI)
    fetch_for_query("shooting in arizona")
      Redis: cache MISS, lock ACQUIRED
      asyncio.gather:
        GoogleNewsSearchAdapter.search()  -> ~30 RawItems (mixed AZ local + wire)
        HackerNewsSearchAdapter.search()  -> 0–5 RawItems
      normalize_items -> dedupe_items -> match_topics -> persist_items
        (any topic-matched articles publish to Redis pubsub here)
      Redis: cache SET (5 min), lock DEL
    SELECT ... WHERE title ILIKE %shooting% AND title ILIKE %arizona% ...
    return results
  SSR renders. SearchStream client takes over polling /api/articles?q every 30s.
```

### Warm search (same query within 5 min)

```
GET /articles?q=shooting+in+arizona
  fetch_for_query(q)
    Redis: cache HIT, return immediately
  SELECT ... return results from DB (already populated by cold fetch)
```

Warm path latency is identical to current search: a single indexed SQL query plus the trivial Redis GET.

## Error handling matrix

| Failure | Behavior | Logged? |
|---------|----------|---------|
| One adapter times out | Other adapter's results flow through | yes |
| Both adapters time out | DB-only results returned | yes |
| Adapter raises | try/except per-adapter inside the adapter; returns `[]` | yes |
| Redis cache `GET` raises | Skip cache, proceed to fetch | yes |
| Redis lock `SET NX` raises | Skip lock, proceed to fetch | yes |
| `persist_items` raises | `fetch_for_query` swallows; route returns DB results | yes |
| `fetch_for_query` raises | Route's try/except swallows; DB query runs as before | yes |

The invariant: a search request returns 200 with whatever the DB has, even if every step of the augmentation failed.

## Performance

- Cold search latency budget: 3s adapter timeout = upper bound. Realistic: 1–2s.
- Warm search latency: unchanged from current (~10–50ms depending on result-set size).
- DB write volume per cold fetch: ~30 INSERTs maximum, dominated by Google News. With dedup, repeat queries write nothing.
- Redis ops per cold fetch: 2 (cache GET miss, lock SET) + 2 (cache SET, lock DEL) = 4. Per warm: 1 (cache GET hit).
- The Redis cache (5 min) and lock (10s expiry) bound the request rate to query-aware sources. A single popular query results in at most ~12 upstream fetches per hour.

## Operational notes

- No new env vars. Reuses `tenjin/db/redis.py` (the lazy singleton from PR #27) and existing pipeline modules.
- No schema change. No migration.
- The 6–8 new background feeds in PR A increase scrape volume by ~10–20% and are subject to the same 5-minute scrape interval. No infra change.
- Google News and HN Algolia have no auth, no quota disclosure, and no rate-limit headers in their responses. The 5-minute cache is a defensive measure; if either upstream tightens, the cache window is the lever to widen.

## What's intentionally out of scope

- Frontend changes. `app/search/page.tsx` and `components/SearchStream.tsx` already work end-to-end. The 30s polling cadence picks up persisted results from the live fetch automatically. No client work needed.
- Surfacing "live results" as a distinct UI section. They appear inline, sorted by `COALESCE(published_at, fetched_at) DESC` with everything else.
- Loading-spinner UI on cold fetches. The SSR await blocks rendering anyway; the existing skeleton state is sufficient.

## Open questions

None — the design has no TBDs. Implementer judgement calls (URL verification for new feeds; trim sizes for fixtures) are documented inline.

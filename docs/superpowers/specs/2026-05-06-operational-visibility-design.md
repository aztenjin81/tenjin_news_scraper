# Operational visibility: public /sources page

Status: design 2026-05-06.

## Problem

The scrape pipeline runs on a flat 5-minute interval across ~60 feeds (RSS, HN, Reddit) plus search-time augmentation from Google News and HN Algolia. Today there is no record of which feeds are alive, which have been silently failing, or which have not yielded an item in days. Adapters log per-attempt, but logs are ephemeral and not aggregated. A feed can quietly die — wrong URL after an outlet redesign, a 403 the User-Agent didn't dodge, a parse-error spike — and the only signal is that articles stop appearing on the topic page.

For an OSINT-leaning audience tracking active conflicts (Iran / US, Ukraine), coverage gaps are the operational concern that matters most. A reader skimming a topic page has no way to know whether "no Tehran Times items today" means there were none, or means we lost the feed three days ago.

## Goals

- Persist per-fetch telemetry so feed health can be reasoned about historically, not just from in-memory logs.
- Classify each feed as `ok` / `lagging` / `silent` against a per-feed expected cadence.
- Expose a public `/sources` page that lists every tracked feed, its current status, and when it last yielded an item. Treat this as a product feature for OSINT-style transparency, not just an internal admin tool.
- Stay inside the existing one-way dependency rule (`api → pipeline → sources/models`). No new infra dependencies.

## Non-goals

- Internal `/admin` dashboard with HTTP status codes, error messages, scheduler queue depth. Deferred — separate spec, reuses the same `feed_fetch_log` table.
- Alerting on silent feeds (Slack / Discord / Sentry / email). Deferred — separate spec.
- Per-topic coverage breakdown ("Iran / US is currently being covered by 14 feeds, 13 are ok"). Deferred — derivable from the same data once we want it.
- Source reliability scoring (publish-lag percentiles, retraction rate). Deferred to v1.1 quality work.
- Adaptive / statistical health thresholds. We picked per-feed expected cadence; revisit only if buckets prove wrong.
- Authentication. The page is fully public.

## Architecture

Two independently shippable PRs, in order:

| PR | Concern | Depends on |
|----|---------|------------|
| **A** | Add `feed_fetch_log` table, cadence config in `feeds.py`, capture in `scrape.run_all()`, prune | Nothing |
| **B** | `pipeline/health.py`, `/sources` endpoint, `app/sources/page.tsx` + proxy | PR A |

PR A can sit in production alone — it just records telemetry no one reads. PR B reads it.

## PR A — Telemetry capture and cadence config

### `feed_fetch_log` table

New SQLAlchemy model in `services/api/tenjin/models/`. New Alembic migration via `alembic revision --autogenerate`.

| column | type | notes |
|---|---|---|
| `id` | `bigint` PK, autoincrement | |
| `source` | `text not null` | feed name from `feeds.py` (e.g. `reuters_world`, `hackernews`) |
| `fetched_at` | `timestamptz not null` | start of the fetch attempt |
| `duration_ms` | `int not null` | wall-clock; `int` is fine since adapters time out at 3–10s |
| `http_status` | `int nullable` | null on transport error or non-HTTP source |
| `error_kind` | `text not null` | `none` / `timeout` / `transport` / `parse` / `http_4xx` / `http_5xx` |
| `items_yielded` | `int not null` | adapter output count, before pipeline dedup |
| `items_persisted` | `int not null` | rows actually inserted (after dedup) |

Indexes:
- `(source, fetched_at desc)` — primary read path: "latest N rows for source X"
- `(fetched_at)` — for the prune pass

No FK to a `sources` table — `source` is the feed name, sourced from `feeds.py` which is code, not data. If a feed is renamed, old rows keep the old name and get pruned out within 30 days.

### Cadence config in `feeds.py`

Existing feed entries are tuples `(name, url, kind, topics)`. Extend to `(name, url, kind, cadence, topics)` where `cadence` is one of:

```python
CADENCE_FAST    = "fast"     # expect new content within 30 minutes
CADENCE_NORMAL  = "normal"   # expect new content within 2 hours
CADENCE_SLOW    = "slow"     # expect new content within 12 hours
CADENCE_RARE    = "rare"     # expect new content within 3 days
```

Constants exported from `sources/feeds.py`. Existing entries get assigned a bucket as part of this change — implementer picks per outlet, with these defaults:

- `wire` kind → `fast` (Reuters, AP, NPR, Al Jazeera EN, BBC, NBC, CBS, ABC, USA Today)
- `regional` kind → `normal` (Times of Israel, Tehran Times, The National, Anadolu)
- `primary` kind → `slow` (US State Dept, ReliefWeb, EU EEAS)
- `state` kind → `slow` (TASS, Press TV) — `rare` for ministerial outlets that only post weekly
- `analysis` kind → `slow` (ISW, CSIS, FDD)
- `social` kind → `fast` (HackerNews, Reddit world)
- IDF Spokesperson, IAEA, ICRC → `rare` (long quiet periods are normal)

`HackerNewsAdapter` (the Firebase top-50 source registered separately from `feeds.py`) gets the same cadence treatment via a small registry shim — see "HN cadence" below.

### Capture point

`workers/scrape.run_all()` already iterates feeds. Wrap the per-feed body:

```python
async def _run_one(feed: FeedEntry, session: AsyncSession) -> None:
    started = time.monotonic()
    error_kind = "none"
    http_status: int | None = None
    items_yielded = 0
    items_persisted = 0
    try:
        adapter = RssAdapter(feed.url, feed.name, feed.kind, feed.topics)
        raw_items = await adapter.fetch()
        items_yielded = len(raw_items)
        normalized = normalize_items(raw_items)
        deduped = await dedupe_items(session, normalized)
        items_persisted = await persist_items(session, deduped, feed.topics)
    except httpx.TimeoutException:
        error_kind = "timeout"
    except httpx.HTTPStatusError as e:
        http_status = e.response.status_code
        error_kind = "http_4xx" if 400 <= http_status < 500 else "http_5xx"
    except Exception:
        error_kind = "transport"
        log.exception("scrape failed", source=feed.name)
    finally:
        await record_fetch(
            session,
            source=feed.name,
            fetched_at=now_utc(),
            duration_ms=int((time.monotonic() - started) * 1000),
            http_status=http_status,
            error_kind=error_kind,
            items_yielded=items_yielded,
            items_persisted=items_persisted,
        )
```

`record_fetch()` is a new helper in `pipeline/health.py` that does a single `INSERT` and commits in its own short-lived transaction (so a failed scrape doesn't lose its log row).

The error classification above is structural — adapters today catch most exceptions internally and return `[]`. The `try/except` in `_run_one` is the safety net for the cases that escape (httpx timeouts on the wrapper level, parse-time crashes in `normalize_items`). Adapters keep their existing "log and return empty list" contract; an empty return looks like `error_kind=none, items_yielded=0`, which is exactly what we want — distinguishable from a transport failure.

`HackerNewsAdapter` is invoked from a different path (`workers/scrape.run_all()` has a special branch for it). Wrap that call with the same `_run_one`-style instrumentation.

### Prune

Extend `pipeline/prune.py`:

```python
async def prune_old_fetch_logs(session, max_age_days: int = 30) -> int:
    cutoff = now_utc() - timedelta(days=max_age_days)
    result = await session.execute(
        delete(FeedFetchLog).where(FeedFetchLog.fetched_at < cutoff)
    )
    return result.rowcount
```

Called from the same scheduler tick that already runs `prune_old_articles`.

### Tests (PR A)

- `test_record_fetch_inserts_row` — write one row, read it back; assert all fields persist.
- `test_run_one_records_success` — fake adapter returning two `RawItem`s; assert exactly one log row written with `error_kind="none"`, `items_yielded=2`, `items_persisted=2`.
- `test_run_one_records_timeout` — fake adapter raising `httpx.TimeoutException`; assert one row written with `error_kind="timeout"`, `items_yielded=0`.
- `test_run_one_records_http_5xx` — fake adapter raising `HTTPStatusError(503)`; assert `http_status=503`, `error_kind="http_5xx"`.
- `test_prune_old_fetch_logs` — insert rows at -10d / -25d / -45d; prune at 30d; assert only the -45d row is gone.

## PR B — Health classification, endpoint, public page

### `pipeline/health.py`

Two functions, both pure read.

```python
@dataclass
class FeedHealth:
    name: str
    label: str
    kind: SourceKind
    cadence: Cadence
    last_item_at: datetime | None
    items_24h: int
    status: Literal["ok", "lagging", "silent"]


@dataclass
class FeedHealthReport:
    summary: dict[str, int]   # {"total": 62, "ok": 58, "lagging": 3, "silent": 1}
    feeds: list[FeedHealth]   # full list, ordered: silent, lagging, ok; secondary by name
    generated_at: datetime


async def compute_feed_health(session) -> FeedHealthReport: ...
```

Implementation:

1. Build the canonical feed list from `feeds.py` plus the registry entries that don't live in `feeds.py` (currently just `hackernews`). This is the source of truth for "what we track" — the report includes a feed even if it has zero log rows (so a freshly-added feed that hasn't fetched yet shows as `silent`, which is honest).
2. Single SQL query: for each `source`, the `MAX(fetched_at) FILTER (WHERE items_persisted > 0)` (= last item time) and `SUM(items_persisted) FILTER (WHERE fetched_at > now() - interval '24 hours')` (= total articles in 24h). PostgreSQL filtered aggregates make this one round-trip.
3. Apply the rule per feed:
   - `ok` if `now - last_item_at <= 1× cadence_interval`
   - `lagging` if `1× < now - last_item_at <= 3× cadence_interval`
   - `silent` if `now - last_item_at > 3× cadence_interval`, or `last_item_at is None`
4. Repeated fetch errors override to `silent`: if the most recent 5 log rows for a source (ordered by `fetched_at desc`, regardless of outcome) all have `error_kind != 'none'`, force `status = "silent"` regardless of `last_item_at`. This catches the "feed has been 403-ing for an hour" case independently of the cadence rule.
5. Build the summary, sort: `silent` first, `lagging` next, `ok` last; within each, alphabetical by `label`.

Cadence intervals as constants in `health.py`:

```python
CADENCE_INTERVALS: dict[Cadence, timedelta] = {
    "fast":   timedelta(minutes=30),
    "normal": timedelta(hours=2),
    "slow":   timedelta(hours=12),
    "rare":   timedelta(days=3),
}
```

### `/sources` endpoint

New file: `services/api/tenjin/api/routes/sources.py`. Registered in `app.py`.

```
GET /sources
```

Returns:

```json
{
  "summary": { "total": 62, "ok": 58, "lagging": 3, "silent": 1 },
  "feeds": [
    {
      "name": "idf_spokesperson",
      "label": "IDF Spokesperson",
      "kind": "primary",
      "cadence": "rare",
      "last_item_at": "2026-05-05T13:42:11Z",
      "items_24h": 0,
      "status": "silent"
    }
  ],
  "generated_at": "2026-05-06T08:51:02Z"
}
```

Schema in `api/schemas/health.py`: `FeedHealthOut`, `FeedHealthReportOut`. Mirror the dataclasses in `pipeline/health.py` exactly. Per the existing rule, never return ORM objects.

**Caching.** Wrap the route with a 30-second in-process TTL cache, keyed by no arguments. The data only changes when `scrape.run_all()` writes new rows (every 5 minutes); 30s is generous and keeps the page snappy under modest traffic. Implementation: a small `cachetools.TTLCache` instance at module level, or a hand-rolled `(value, expires_at)` tuple — either is fine. No Redis needed; this is one query per cache window.

### Frontend

Two files on the web side, mirroring the existing topic-page pattern.

`apps/web/app/api/sources/route.ts` — same-origin proxy to backend `/sources`. Standard wrapper, identical pattern to `app/api/articles/route.ts`. Browser stays same-origin; no CORS, no public API URL.

`apps/web/app/sources/page.tsx` — SSR page. Server Component. Calls the proxy via `lib/api.ts` (add `fetchSources()` there). Renders the **B layout** the user picked:

- Eyebrow: `SOURCES · {summary.total} TRACKED · UPDATED {age} AGO`
- Three count cards in a row: ok / lagging / silent, color-coded via existing tokens (`--src-{kind}-fg` is the wrong namespace — use new tokens: `--status-ok`, `--status-warn`, `--status-bad`, defined in `globals.css` to match the existing accent palette).
- "Silent" section — list of silent feeds with name, kind pill, last-seen-ago.
- "Lagging" section — same, for lagging feeds.
- "All sources" section — full list, **grouped by kind** within this section (wire / regional / primary / state / analysis / social), each row: name, last-seen-ago, items in 24h, status dot.

Reuses `SourcePill` (already exists per `apps/web/CLAUDE.md`). New small component `StatusDot` for the pulsing-or-solid state indicator. Uses `LiveIndicator`-style "Updated Xs ago" pattern at the top.

The page is SSR-only — no client streamer. `revalidate = 30` in the route segment config gives a 30s ISR window that aligns with the API cache. The data refreshes naturally on next request after that window.

`generateMetadata`: title `Sources — Tenjin News`, canonical `/sources`, brief description. Standard.

Header link: add "Sources" to the nav in `components/Header.tsx`.

### Tests (PR B)

- `test_compute_feed_health_classifies_ok` — log row 10 minutes ago for a `fast`-cadence feed, items_persisted=1; assert `status="ok"`.
- `test_compute_feed_health_classifies_lagging` — log row 90 minutes ago for `fast`; assert `status="lagging"`.
- `test_compute_feed_health_classifies_silent_by_age` — log row 4 hours ago for `fast`; assert `status="silent"`.
- `test_compute_feed_health_classifies_silent_by_errors` — last 5 rows all errors, last item_persisted within 1× cadence; assert `status="silent"`.
- `test_compute_feed_health_includes_zero_log_feed` — feed in registry with no log rows; assert it appears with `status="silent"`, `last_item_at=null`, `items_24h=0`.
- `test_compute_feed_health_summary_counts` — fixture with 3 ok / 2 lagging / 1 silent; assert summary numbers.
- `test_compute_feed_health_sort_order` — silent before lagging before ok; alphabetical within.
- `test_sources_route_returns_report` — integration: hit `/sources`, parse JSON, assert shape and field types.
- `test_sources_route_cached` — call twice within 30s; assert `compute_feed_health` was invoked once.
- Web: snapshot test of `app/sources/page.tsx` rendering against a fixture report (vitest + happy-dom). Assert the three count cards and at least one silent-section row.

## Data flow

```
Every 5 minutes:
  scheduler -> scrape.run_all()
    for each feed in feeds.py + extra_registry:
      _run_one(feed):
        adapter.fetch()
        normalize -> dedupe -> persist
        record_fetch(...)   <- new

User visits /sources:
  Next.js SSR -> /api/sources (proxy) -> FastAPI /sources
    cache check (30s in-process)
      MISS:
        compute_feed_health(session):
          read feeds.py + extra_registry
          one SQL query: per-source last_item_at + items_24h
          read last 5 rows per source (for error override)
          classify, sort, build summary
        cache SET
      HIT: return cached
  Page renders. revalidate=30 keeps the SSR fresh.

Daily (or every scheduler tick):
  prune_old_articles()
  prune_old_fetch_logs(max_age_days=30)   <- new
```

## Error handling

| Failure | Behavior |
|---|---|
| `record_fetch` insert fails | Log; the scrape itself is unaffected (already committed). |
| `compute_feed_health` SQL query fails | Route returns 500. Page renders an empty-state error component (defer fancy retry UI). |
| Feed in `feeds.py` has unknown cadence string | Default to `normal`; log warn at startup. |
| Backend unreachable from web SSR | Existing `lib/api.ts` fallback to fixtures (per `apps/web/CLAUDE.md`); a stub `sources` fixture is added so the page renders in dev without the backend. |

## Performance

- Telemetry write volume: ~17k rows/day at 60 feeds × 12 fetches/hour. 30-day retention → ~520k rows steady-state. Trivial.
- `compute_feed_health` SQL: one filtered-aggregate query, ~60 groups, indexed on `(source, fetched_at desc)`. Sub-10ms even cold. Plus one `SELECT TOP 5` per source for the error-override check (60 small indexed scans).
- Endpoint latency: cache hit < 1ms; cache miss ~20ms. Page SSR: 30s ISR, so practical render is sub-200ms.
- No new Redis usage. No new external HTTP calls.

## Operational notes

- No new env vars. No new infra.
- `feeds.py` schema change is backwards-incompatible at the parsing level (extra tuple element). Implementer must update every existing entry as part of PR A; CI will fail loudly if any are missed because the unpacking destructures all five fields.
- Migration is additive — `feed_fetch_log` is a new table. No schema change to existing tables. Rollback = drop the table.

## What's intentionally out of scope

- Internal `/admin` view. Same telemetry feeds it; separate spec.
- Alerting on silent feeds (Slack / Discord / Sentry / email). Same telemetry feeds it; separate spec.
- Per-topic coverage breakdowns. Derivable; defer.
- Source reliability scoring. Roadmap v1.1.
- Charts / sparklines on the public page. Site convention is text-only, no charts.
- Adaptive thresholds. Revisit if buckets prove wrong.

## Open questions

None. Implementer judgement calls (per-feed bucket assignment in `feeds.py`, exact `--status-*` token values in `globals.css`) are documented inline.

# services/api — CLAUDE.md

FastAPI app + scraper workers. Read this before editing under `services/api/`.

## Module map

```
tenjin/
├── api/                       HTTP layer (FastAPI app, routes, dependencies)
│   ├── app.py                 App factory + middleware + router registration
│   ├── deps.py                Shared FastAPI dependencies (db session, settings)
│   ├── routes/
│   │   ├── articles.py        /articles (topic, q, before filters)
│   │   ├── topics.py          /topics (24h counts)
│   │   ├── sources.py         /sources — public coverage transparency, 30s in-process cache
│   │   ├── stream.py          /stream/topic/{slug} — SSE, subscribes to Redis pubsub
│   │   └── health.py
│   └── schemas/
│       ├── article.py         ArticleOut + to_article_out() — wire shape, shared by routes and SSE
│       └── health.py          FeedHealthOut / FeedHealthReportOut — /sources wire format
├── sources/                   Source adapters. One file per source family.
│   ├── base.py                SourceAdapter protocol + shared helpers
│   ├── registry.py            Maps source name → adapter class
│   ├── feeds.py               Central RSS/Atom feed registry (URLs + topic hints), iterated by scrape.run_all()
│   ├── rss.py                 Generic RSS/Atom adapter (used by every entry in feeds.py)
│   └── hackernews.py          Firebase top-50 adapter
├── pipeline/                  Normalize → dedupe → topic-match → persist → publish
│   ├── normalize.py           RawItem → canonical Article fields
│   ├── dedupe.py              URL + title fingerprint
│   ├── topic_match.py         Topic registry → topic_matches rows
│   ├── persist.py             persist_items() — writes Articles + topic_matches in one tx
│   ├── publish.py             publish_article_to_topics() — Redis pubsub fanout (best-effort, post-commit)
│   ├── health.py              record_fetch() telemetry insert + classify() + compute_feed_health() (powers /sources)
│   └── prune.py               Drops articles older than max-age (also feed_fetch_log at 30 days)
├── topics/                    Topic definitions, query parsing, entity rules
│   ├── registry.py
│   └── presets.py
├── models/                    SQLAlchemy ORM models (data only — no business logic)
├── db/
│   ├── session.py             Async engine + session factory
│   ├── redis.py               Lazy singleton Redis client (decode_responses=True)
│   ├── bootstrap.py           Optional create-all for local dev
│   └── migrations/            Alembic
├── workers/
│   ├── scrape.py              run_all() — iterate feeds, run pipeline
│   └── scheduler.py           APScheduler loop, calls scrape.run_all every SCRAPE_INTERVAL_SECONDS
└── config.py                  pydantic-settings — single source of truth for env
```

## Conventions

- **Async** by default for I/O. Use `httpx.AsyncClient`, `asyncio` primitives. Workers are sync (RQ); they call into async code via `asyncio.run`.
- **Routes are thin.** A handler should: parse request → call a service or pipeline function → shape response. No DB queries inline in routes longer than two lines.
- **Schemas vs models.** SQLAlchemy classes in `models/` are storage. Pydantic classes in `api/schemas/` are wire format. Never return ORM objects from a route.
- **Settings.** All env access goes through `tenjin.config.Settings`. Don't `os.getenv` from feature code.
- **Logging.** `structlog`, key-value style. Include `source`, `url`, `topic` where relevant.
- **Errors from sources are normal.** Adapters must not raise to the worker; they log and return an empty list. The worker keeps going.
- **Adapters declare a cadence.** Every concrete `SourceAdapter` exposes a `cadence: str` attribute — one of `fast` (≤30 min expected), `normal` (≤2 h), `slow` (≤12 h), or `rare` (≤3 days). The `/sources` health classifier uses this to decide whether a feed is `ok` / `lagging` / `silent`.
- **Telemetry is captured in `run_adapter`, not in adapters.** `workers/scrape.run_adapter` wraps every fetch with timing + outcome capture and writes one `feed_fetch_log` row via `pipeline.health.record_fetch` in a separate session, so the telemetry row commits independently of `persist_items` (a failed persist still records a row with the right `error_kind`).
- **Redis pubsub is best-effort and post-commit.** `pipeline.publish.publish_article_to_topics()` runs *after* `session.commit()` succeeds in `persist_items()`, never before — never publish data that could be rolled back. The publish call is wrapped in try/except: a Redis outage logs and continues, and persistence must never block on it.

## Adding a source adapter

1. New file under `tenjin/sources/<name>.py`.
2. Implement `SourceAdapter` from `sources/base.py` — `name`, `cadence` (`fast`/`normal`/`slow`/`rare`), `fetch() -> list[RawItem]`. Pick `cadence` based on how often the source is *expected* to publish, not how often you scrape it.
3. Register the adapter **class** in `sources/registry.py` (maps source name → adapter class). For RSS/Atom feeds reusing `rss.RssAdapter`, also append the feed **URL** + cadence (and topic hints) to `sources/feeds.py` — that's what `scrape.run_all()` iterates.
4. Add a fixture under `tests/sources/fixtures/<name>/` and a test that asserts at least one normalized article comes out.
5. If the source needs credentials, add the env var to `infra/.env.example` and read it through `config.Settings`.

## Database changes

```bash
alembic revision --autogenerate -m "describe change"
# review the generated file — autogenerate is not perfect
alembic upgrade head
```

## Don't

- Don't add a new top-level package without updating this map.
- Don't import from `api/` into `pipeline/` or `sources/` (one-way dependency: `api → pipeline → sources/models`).
- Don't put business logic in `models/`. Keep ORM classes data-only.

## Windows dev quirk

`psycopg` async mode is incompatible with the `ProactorEventLoop` that asyncio uses by default on Windows. Three places this hits:

- **Alembic migrations** — handled in `db/migrations/env.py` (sets `WindowsSelectorEventLoopPolicy` before constructing the async engine).
- **Pytest** — handled in `tests/conftest.py` (same policy, set at collection time so async fixtures can connect).
- **Uvicorn dev server** — pass `--reload` (which sets `use_subprocess=True` internally and routes through `SelectorEventLoop`). Without `--reload`, every DB-touching route 500s on Windows. The local-dev command in the root README already uses `--reload`.

All three fixes are `sys.platform == "win32"` gated; Linux/CI is unaffected.

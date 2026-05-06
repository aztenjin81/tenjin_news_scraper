# services/api — CLAUDE.md

FastAPI app + scraper workers. Read this before editing under `services/api/`.

## Module map

```
tenjin/
├── api/              HTTP layer (FastAPI app, routes, dependencies)
│   ├── app.py        App factory + middleware + router registration
│   ├── deps.py       Shared FastAPI dependencies (db session, settings)
│   └── routes/       One file per resource. Handlers stay thin.
├── sources/          Source adapters. One file per source family.
│   ├── base.py       SourceAdapter protocol + shared helpers
│   ├── registry.py   Maps source name → adapter class
│   └── ...           rss.py, html.py, gdelt.py, ...
├── pipeline/         Normalize → dedupe → topic-match → persist
├── topics/           Topic definitions, query parsing, entity rules
├── models/           SQLAlchemy ORM models
├── db/               Engine, session, migrations
├── workers/          RQ job definitions (called by `rq worker`)
└── config.py         pydantic-settings — single source of truth for env
```

## Conventions

- **Async** by default for I/O. Use `httpx.AsyncClient`, `asyncio` primitives. Workers are sync (RQ); they call into async code via `asyncio.run`.
- **Routes are thin.** A handler should: parse request → call a service or pipeline function → shape response. No DB queries inline in routes longer than two lines.
- **Schemas vs models.** SQLAlchemy classes in `models/` are storage. Pydantic classes in `api/schemas/` are wire format. Never return ORM objects from a route.
- **Settings.** All env access goes through `tenjin.config.Settings`. Don't `os.getenv` from feature code.
- **Logging.** `structlog`, key-value style. Include `source`, `url`, `topic` where relevant.
- **Errors from sources are normal.** Adapters must not raise to the worker; they log and return an empty list. The worker keeps going.

## Adding a source adapter

1. New file under `tenjin/sources/<name>.py`.
2. Implement `SourceAdapter` from `sources/base.py` — `name`, `fetch() -> list[RawItem]`.
3. Register in `sources/registry.py`.
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

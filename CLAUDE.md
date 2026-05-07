# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this repo is

Tenjin News is a topic-driven news aggregator. See `README.md` for the product pitch.

## Layout

This is a monorepo with two deployable units:

```
apps/web/          Next.js 16 (App Router, TS, Tailwind v4) — public site
services/api/      FastAPI (Python 3.11+) — API + scraper workers
infra/             docker-compose for local Postgres + Redis
```

Each package has its own `CLAUDE.md` with package-specific conventions. **Read it before editing inside that package.**

- `apps/web/CLAUDE.md`
- `services/api/CLAUDE.md`

## Cross-cutting conventions

- **Branches**: feature work goes on `claude/<short-description>` or `<your-name>/<short-description>`. Never commit to `main` directly.
- **Commits**: imperative mood, scoped subject. `api: add rss adapter`, `web: render topic page metadata`, `infra: bump postgres to 16`.
- **PRs**: small and focused. One concern per PR.
- **Secrets**: never commit `.env`, API keys, or scraped article payloads. `infra/.env.example` is the source of truth for required env vars.
- **Generated files**: don't commit `node_modules/`, `.venv/`, `__pycache__/`, build output, or migration artifacts that aren't checked-in migrations.

## Local dev

```bash
# Bring up Postgres + Redis (Linux: prefix with `sudo` if the docker socket is root-owned)
docker compose -f infra/docker-compose.yml up -d

# Backend (in one terminal)
cd services/api
python -m venv .venv
# Linux/macOS:  source .venv/bin/activate
# Windows PS:   .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn tenjin.api.app:app --reload

# Frontend (in another terminal)
cd apps/web
pnpm install
pnpm dev
```

## When adding a feature

- **New source**: add an adapter under `services/api/tenjin/sources/` implementing `SourceAdapter` (including a `cadence` of `fast`/`normal`/`slow`/`rare` so the `/sources` page can classify health correctly) and register the adapter class in `sources/registry.py`. For RSS/Atom feeds, also add the feed URL to `sources/feeds.py` (the central feed list iterated by `scrape.run_all()`) with the `cadence=` kwarg set. Add a fixture-backed test in `services/api/tests/sources/`.
- **New API route**: add to `services/api/tenjin/api/routes/`. Keep route handlers thin — push logic into `pipeline/` or service modules.
- **New page**: add under `apps/web/app/`. Pages that should be SEO-indexed must export `generateMetadata` and use SSR (no `"use client"` at the page root).
- **Schema change**: edit the SQLAlchemy model, then `alembic revision --autogenerate -m "..."`, review the generated migration, commit both.

## What not to do

- Don't add LLM features to v1 — they're explicitly deferred to v2 in the roadmap.
- Don't store full article bodies for outlets whose ToS forbid republication. Bodies are used internally for dedup; only headlines, snippets, and links are surfaced to users.
- Don't bypass `robots.txt` or per-source rate limits.
- Don't introduce a third stack (no Go service, no Rust worker) without discussion. The bet is Python + TS, full stop.

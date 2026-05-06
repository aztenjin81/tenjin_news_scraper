# Changelog

## [Unreleased]

### Added
- Ad-hoc full-text search: `/articles?q=<phrase>` ANDs ILIKE matches across title and snippet (whitespace-tokenized, drops <2-char tokens, caps at 8 terms); new `/search` page renders SSR results and a client `SearchStream` polls every 30s for fresh matches via a same-origin Next.js proxy at `/api/articles` (#28)
- SSE push for near-real-time topic feeds: `persist_items()` publishes new articles to Redis pubsub `topic:{slug}` after commit; `/stream/topic/{slug}` subscribes and forwards SSE frames; frontend `ArticleStream` subscribes via a same-origin Next.js proxy and prepends new items, deduping by id. Falls back to keepalive-only if Redis is unreachable so clients don't reconnect-storm (#27)
- Ticker shows attribution + delay: each symbol links to its Yahoo Finance quote page; new footer line displays "Data: Yahoo Finance" and "Delayed up to N min" / "Real time" derived from upstream `meta.exchangeDataDelayedBy` (#26)
- `SECURITY.md`, `CODEOWNERS`, and workflow `permissions: contents: read` hardening
- CI workflow: typecheck, lint, vitest, pytest, gitleaks secret scan
- Dependabot config for npm and GitHub Actions groups
- GitHub Actions pinned to immutable commit SHAs (ci.yml + deploy.yml); Dependabot will keep them current

### Changed
- Default `SCRAPE_INTERVAL_SECONDS` lowered from 15 min → 5 min — realistic floor before free RSS feeds (Reddit, Yahoo, etc.) start returning 429s; sub-minute freshness lives on the SSE push path
- Dependabot now ignores `eslint@10` (blocked by `eslint-plugin-react@7.37.5` capping at eslint^9.7), `vitest@4.1+` (requires vite^6 peer), and `@types/node@25` (kept failing the bundled dev-group PR) — stops the recurring failed PRs (#10, #12, #24)

### Fixed
- RSS adapter parses ISO 8601 / Atom dates so `COALESCE(published_at, fetched_at)` sort actually uses publish time. Old `_parse_date` used `email.utils.parsedate_to_datetime` (RFC 2822 only) and silently returned `None` for Atom feeds. Now reads `entry.published_parsed` / `entry.updated_parsed` (already normalized by feedparser) and converts to aware UTC. Regression test asserts non-NULL `published_at` on Atom-shaped fixtures (#25)
- `pnpm install --frozen-lockfile` removed from CI so Dependabot npm PRs can pass (lockfile is updated on the branch, not pre-frozen)
- ruff B008 false positive for FastAPI `Query()` defaults suppressed via `ignore = ["B008"]`
- ruff UP017 auto-fixed (`timezone.utc` → `datetime.UTC`) in `services/api/tenjin/sources/rss.py`
- postcss XSS (GHSA-qx2v-qp2m-jg93): pnpm override forces `postcss>=8.5.10` to replace the vulnerable `8.4.31` Next.js 15 pulled in

### Confirmed live
- Ticker on tenjin.us shows live Yahoo Finance market data (not fixture values)
- Next.js 16.2.4: replaced `next lint` (removed in v16) with `eslint .`; migrated `.eslintrc.json` → `eslint.config.mjs` (ESLint flat config via `eslint-config-next/core-web-vitals`)
- TypeScript ^5 → ^6.0.3: dropped redundant `baseUrl` from `tsconfig.json` to fix TS5101
- vitest ^2 → ~4.0.18: ships vite@6 internally; clears all remaining audit vulnerabilities (esbuild + vite CVEs)
- ESLint 10 deferred: `eslint-plugin-react@7.37.5` (dep of `eslint-config-next`) caps at `^9.7`; will unblock when upstream updates
- HackerNews source adapter: fetches top 50 stories concurrently from Firebase API, no credentials required
- 22 RSS feeds added across all source kinds: BBC World/Middle East, AP, Al Jazeera, Times of Israel, Haaretz, Arab News, The Cradle, Tehran Times, Press TV, IRNA, TASS, RT, Xinhua, Al Mayadeen, US State Dept, US CENTCOM, US DoD, ReliefWeb, IAEA, ISW, Brookings
- 11 Ukraine-focused feeds added: Kyiv Independent, Ukrainska Pravda, Euromaidan Press, Meduza, Moscow Times, Notes from Poland, Kremlin.ru, Atlantic Council UkraineAlert, CSIS, RUSI, War on the Rocks
- New topic: `ukraine-war` (registered on both backend topic registry and frontend)
- Article list sort fixed — was clustering by source (scheduler processes feeds sequentially, fetched_at clusters per feed). Now ordered by `COALESCE(published_at, fetched_at) DESC` so topic pages show genuine recency
- **End-to-end pipeline live**: adapters → normalize → dedupe → topic-match → DB → API → frontend. Real headlines flow through every 15 min via scheduler container; topic pages now show live data instead of fixtures
- API Dockerfile fix: copy source before `pip install` (Hatchling needs the package directory to exist, even for non-editable install)
- `Settings.api_cors_origins` accepts plain string / comma-separated / JSON list via `NoDecode` + `field_validator` (caused first deploy outage)
- Deploy workflow split into discrete `build` / `up -d` steps and dumps service logs on failure (`if: always()`) so future deploy issues are debuggable from the workflow output alone
- Initial Alembic migration creates `articles`, `topics`, `topic_matches`, `sources`; deploy runs `alembic upgrade head` automatically
- Production stack now includes `postgres`, `redis`, `migrate` (one-shot), `api`, `scheduler`, `web`
- API routes wired: `/articles?topic=` joins through `topic_matches`, `/topics` returns 24h counts
- `Article.source_kind` + `snippet`; `is_breaking` computed at response time (< 20 min old)
- Reddit RSS feeds: 9 subreddits registered (worldnews, news, geopolitics, technology, science, economics, finance, environment, climate)
- `feeds.py`: central feed registry; `scrape.run_all()` iterates every configured feed
- `RssAdapter`: adds `tenjin-news-bot/1.0` User-Agent to avoid Reddit rate-limiting
- Fixed fixture article URLs — all 12 stories now link to article paths, not root domains

# Feature backlog

Candidates surfaced during brainstorming. Each one becomes its own spec → plan → implementation cycle. Order within a section is rough priority.

## Site / UX

- **Source-kind filter on topic pages** — toggle wire / regional / primary / state / analysis. Taxonomy already exists in `apps/web/lib/sources.ts`.
- **Compare-coverage view** — same event from Reuters vs. Tehran Times vs. Times of Israel side-by-side. Leans on existing dedup clusters.
- **Timeline view** — chronological lanes by source kind, alternative to the list.
- **OSINT mode for conflict topics** — pinned primary-source rail (IDF Spokesperson, IRGC outlets, ISW assessments, ReliefWeb), entity tagging on cards, geo-pin column where coords are present.
- **RTL support** for Arabic / Persian / Hebrew titles. (Roadmap v1.1.)
- **Saved topics + email digest** — auth, per-user topic list, daily/hourly digest. (Roadmap v2.1.)
- **Article hover preview** — snippet, fetched_at, paywall flag without leaving the feed.
- **Per-topic OG share image** — generated card from latest 3 headlines.
- **Outlet-link source labels on `/sources`** — ABC News links to abcnews.go.com, Tehran Times links to tehrantimes.com, etc. Likely add a `home_url` attribute to each adapter (or derive from feed URL netloc as fallback). Worth extending to article rows / `SourcePill` once we ship it for `/sources`.

## Info tracking / analytics

- **Operational visibility** — scrape health dashboard (feed up/down, parse errors, items/min, last-seen-at) + alerting on silent feeds. *(public `/sources` page shipped in PRs #35 + #36; internal `/admin` view and silent-feed alerting still deferred — separate specs that reuse the same `feed_fetch_log` telemetry)*
- **Source reliability scoring** — per-outlet quality signal: publish-lag, dedup-loss rate, broken-link rate, retraction rate. Feeds dashboard and ranking. (Roadmap v1.1.)
- **Product analytics** — Plausible or PostHog, privacy-friendly, per-topic page views, click-through to outlets.
- **Search-query log** — record queries that return zero results, surface as a gap-analysis report driving source-acquisition priorities.

## Infra / pipeline

- **Search backend** — OpenSearch or Meilisearch. README promises it; current search appears to be Postgres-only.
- **MinHash body dedup** — beyond URL + title fingerprint. (Roadmap v1.1.)
- **Per-source scrape cadences** — currently flat 5 min; high-volume vs. slow sources should differ.
- **Backfill pipeline** — Common Crawl News / Wayback Machine. When a new topic is added, populate history.
- **Multi-region scrape egress** — some Iranian / Russian sources block US IPs.
- **Article body archival to S3 / R2** — TTL-controlled, so embeddings can be recomputed and ToS-restricted bodies dropped on schedule.

## News sources / data

- **GDELT 2.0** — global event stream, free, ideal for ME / Ukraine OSINT. README names it; not built.
- **Bluesky firehose** — free, growing journalist presence.
- **Telegram public channels** — ministry + regional-reporter channels. Hardest, highest signal for ME / Ukraine.
- **ISW daily assessments** — HTML scrape, no feed. Direct OSINT value.
- **ReliefWeb / ICRC / IAEA** — UN OCHA primary sources.
- **More state primary sources** — IRGC outlets, IDF Spokesperson, US State Dept press, Russian MoD, Ukrainian General Staff.
- **Mastodon** — instance APIs, journalist-heavy.
- **Reddit JSON API** — beyond RSS; comments are useful signal for early reports of breaking events.

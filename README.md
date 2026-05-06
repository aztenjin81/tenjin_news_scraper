# Tenjin News

> A live, topic-driven news aggregator. Tell it a topic — `iran`, `houthis`, `strait of hormuz`, `nancy guthrie` — and it keeps a continuously refreshed feed of every article, post, and report it can find on the open web.

**Launch focus:** Iran / US tensions and the wider Middle East — Israel, Gaza, Lebanon, Yemen / the Houthis, Syria, Iraq, the Gulf states, and US policy responses. The platform is built to extend to any topic, but Middle East coverage is what we're shipping first and what we intend to be excellent at.

---

## What it is

Tenjin News is a **pure aggregator**. It does not write articles, it does not editorialize, and (for now) it does not summarize. It does one thing well:

1. You give it a topic.
2. It pulls from every source it knows about — wire services, major outlets, regional press, social platforms, government and NGO releases, think-tank publications.
3. It deduplicates, ranks by recency and source diversity, and serves the result as a fast, SEO-friendly page that updates live.

LLM-powered summaries, clustering, and bias labeling are on the roadmap, not in v1.

## Why another aggregator

Most aggregators either (a) only show you a handful of mainstream sources or (b) bury regional and primary-source reporting under whatever the algorithm thinks you want. For a fast-moving conflict story, that's the wrong shape. Tenjin's bet is that a reader following Iran/US should see Reuters, *and* Tehran Times, *and* Times of Israel, *and* the IDF spokesperson's feed, *and* ISW's daily assessment — in one place, in time order, with the source labeled honestly.

## Features (v1)

- **Topic search** — any free-text query becomes a live feed (`/t/iran`, `/t/houthis-red-sea`).
- **Multi-source collection** — RSS/Atom, HTML scraping, news APIs, and social platforms (see [Sources](#sources)).
- **Live updates** — feeds refresh continuously; the frontend streams new articles in without a full reload.
- **SEO-first rendering** — server-side rendered topic pages with structured data (`NewsArticle`, `CollectionPage`) so Google can index them properly.
- **Source transparency** — every item shows outlet, original URL, fetch time, and collection method.
- **Dedup and clustering (lightweight)** — near-duplicate detection across wires so you don't see the same AP story five times.
- **Middle East–tuned defaults** — curated source list, geographic and actor entity lists, and topic presets for the launch vertical.

## Tech stack

| Layer        | Choice                                    | Why                                                                 |
|--------------|-------------------------------------------|---------------------------------------------------------------------|
| Frontend     | Next.js (App Router, TypeScript)          | SSR/ISR for SEO, streaming for live updates, mature ecosystem.      |
| Backend API  | FastAPI (Python 3.11+)                    | Async, fast, great fit for the scraping pipeline.                   |
| Scrapers     | `feedparser`, `httpx`, `Playwright`, `snscrape`, GDELT client | Best-in-class Python tooling per source type. |
| Queue        | Redis + RQ (or Celery)                    | Schedule and fan out scrape jobs; keep the API process light.       |
| Storage      | Postgres (articles, sources, topics) + OpenSearch / Meilisearch (search) | Relational truth + fast full-text on titles and bodies. |
| Cache / live | Redis pub/sub + Server-Sent Events        | Push new articles to open topic pages without polling.              |
| Deploy       | Vercel (frontend) + Fly.io / Railway (API + workers) | Cheap, fast, good DX for both halves.                      |

## Sources

The collector is designed as a set of pluggable adapters. v1 ships with all of the following, and adding a new one is a single file under `services/api/sources/`.

**Feeds (RSS / Atom)** — the backbone. Reuters, AP, AFP, BBC, Al Jazeera English & Arabic, Times of Israel, Haaretz, Tehran Times, Press TV, Al-Monitor, Middle East Eye, Asharq Al-Awsat, The National (UAE), Arab News, Anadolu, TASS, Xinhua, plus US outlets (NYT, WaPo, WSJ, Bloomberg, Politico, Axios) where feeds exist.

**HTML scraping (Playwright)** — for outlets without feeds, or where feeds truncate. Resilient selectors, screenshot-on-failure, and a per-site rate limit. We respect `robots.txt` and per-outlet ToS; sources that disallow scraping are collected via API or feed only.

**News APIs** — GDELT 2.0 (free, global event + article stream), NewsAPI, Google News RSS (per-query), Bing News, Common Crawl News for backfill.

**Social** — X/Twitter (paid API tier, official + journalist lists), Bluesky (firehose, free), Mastodon (instance APIs), Reddit (r/worldnews, r/syriancivilwar, r/IRstudies, etc.), Telegram public channels (regional reporters, official ministry channels), Truth Social *(exploratory — no public API; via mirrored feeds where legal)*.

**Primary sources** — US State Dept and DoD press releases, IDF Spokesperson, IRGC / Iranian state media, UN OCHA ReliefWeb, ICRC, IAEA, EU EEAS.

**Analysis & think tanks** — ISW (Institute for the Study of War), CSIS, FDD, Crisis Group, Chatham House, RUSI, Carnegie Middle East, Brookings, Wilson Center.

**Long-form & podcasts** — selected podcast RSS (transcripts when available) for retrospective context.

If you know a source we should add, open an issue with the feed URL or scrape pattern.

## How a topic feed works

```
            ┌────────────┐
   user ───►│ /t/iran    │  Next.js page (SSR + streaming)
            └─────┬──────┘
                  │ 1. SSR fetches latest 50 articles for topic from API (cached)
                  │ 2. Page hydrates and opens an SSE connection
                  ▼
            ┌────────────┐
            │  FastAPI   │
            └─────┬──────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  Postgres (articles)   Redis pub/sub (live updates)
        ▲                   ▲
        │                   │
   ┌────┴────────────────────────┐
   │  Scraper workers (RQ)       │
   │  - feed adapters (every 1m) │
   │  - html adapters (every 5m) │
   │  - social adapters (stream) │
   │  - api adapters (every 2m)  │
   └─────────────────────────────┘
```

Each scraped article is normalized to a common schema (`url`, `canonical_url`, `title`, `outlet`, `author`, `published_at`, `fetched_at`, `body`, `lang`, `entities`, `topics`), deduped against the last 48h, and matched to any topic whose query terms or entity rules apply. Matching topics get a Redis publish so any open page updates in real time.

## Project layout (planned)

```
tenjin_news_scraper/
├── apps/
│   └── web/                 # Next.js (App Router, TS) — public site
├── services/
│   └── api/                 # FastAPI app + scraper workers
│       ├── sources/         # one adapter per source type
│       ├── pipeline/        # normalize, dedupe, topic-match
│       ├── topics/          # topic definitions + matchers
│       └── api/             # HTTP + SSE routes
├── infra/                   # docker-compose, deploy configs
├── CLAUDE.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Getting started

> Nothing past the docs is implemented yet. These are the commands the repo will support once the scaffolding lands.

```bash
# Clone
git clone https://github.com/aztenjin81/tenjin_news_scraper.git
cd tenjin_news_scraper

# Backend
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres redis            # local infra
alembic upgrade head                            # migrate
uvicorn tenjin.api:app --reload                 # API on :8000
rq worker scrape                                # one or more workers

# Frontend
cd ../../apps/web
pnpm install
pnpm dev                                        # site on :3000
```

## Roadmap

- **v1 — Aggregator.** Topic search, all source adapters, live updates, SEO pages. *(in progress)*
- **v1.1 — Quality.** Better dedup (MinHash on bodies), source reliability scores, language filters, RTL support for Arabic / Persian / Hebrew titles.
- **v2 — Intelligence layer (LLM, optional).** Per-topic AI summaries, event clustering ("Strait of Hormuz incidents — March"), automatic entity tagging, multi-language translation of headlines.
- **v2.1 — Personalization.** Saved topics, email/RSS digests, push alerts on breaking items.
- **v3 — Public API.** Read-only API for researchers and journalists.

## Legal & ethical posture

- We respect `robots.txt` and per-source rate limits.
- We store and display **headlines, snippets, metadata, and links** — not full article bodies for outlets whose ToS forbid republication. Body text is used internally for dedup and (later) summarization.
- Outlets are always credited and linked. Our goal is to send readers *to* original publishers, not to replace them.
- Source labels are honest: state media is labeled as state media, think tanks are labeled with their funding orientation where it's a matter of public record.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). The fastest way to help right now is to suggest sources we're missing, especially regional / non-English outlets.

## License

MIT — see [LICENSE](./LICENSE).

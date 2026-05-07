# apps/web — CLAUDE.md

Next.js 16 (App Router, TypeScript, Tailwind v4) — public site.

## Layout

```
app/
├── layout.tsx                       Root layout, header/footer, fonts, global metadata
├── page.tsx                         Home — hero (title + lede + search) + Ticker + featured topics
├── globals.css                      Tailwind import + theme tokens + keyframes
├── about/page.tsx                   /about — what we do / don't do, source taxonomy
├── search/page.tsx                  /search?q=… — SSR initial results + SearchStream polling
├── sources/page.tsx                 /sources — coverage-transparency feed health (SSR + ISR, status-first layout)
├── t/[topic]/page.tsx               Topic feed (SSR + ISR) — eyebrow, H1, LiveIndicator, ArticleStream
├── t/[topic]/not-found.tsx          Custom 404 voice for unknown topics
├── api/articles/route.ts            Same-origin proxy → backend /articles (used by SearchStream)
├── api/sources/route.ts             Same-origin proxy → backend /sources (used by /sources page)
├── api/quotes/route.ts              Same-origin proxy → backend market quotes (used by Ticker)
└── stream/topic/[slug]/route.ts     Same-origin SSE proxy → backend /stream/topic/{slug}

components/
├── Header.tsx                       Logomark + wordmark text + nav links
├── Footer.tsx
├── Logomark.tsx                     Inline SVG (six bars, rightmost in --accent)
├── SearchBar.tsx                    (client) free-text → /search?q=<query>
├── SearchStream.tsx                 (client) polls /api/articles?q every 30s, prepends new matches
├── ArticleStream.tsx                (client) subscribes to SSE proxy, prepends new articles, dedupes by id
├── Ticker.tsx                       (client) postage-stamp markets grid with sparklines
├── TopicTile.tsx                    Featured-topic card
├── ArticleRow.tsx                   Single headline row with SourcePill + meta
├── SourcePill.tsx                   Color-coded badge per source kind
├── StatusDot.tsx                    Small dot for feed health (--status-ok/warn/bad), used on /sources
├── LiveIndicator.tsx                (client) pulsing dot + "Updated Xs ago"
└── EmptyState.tsx

lib/
├── api.ts                           Article/Topic types + fetchers (incl. searchArticles, fetchSources, FeedHealth/FeedHealthReport)
├── topics.ts                        TOPICS list, slugify, header subset
├── sources.ts                       SourceKind taxonomy + labels/examples
├── quotes.ts                        Yahoo Finance quote shape + fetch helpers
└── fixtures.ts                      Demo articles + FIXTURE_SOURCES_REPORT for the design preview

public/
├── logomark.svg                     Six-bar logomark
├── wordmark.svg                     Logomark + "Tenjin News" text
└── favicon.svg                      Square favicon
```

## Conventions

- **Server Components by default.** Mark `"use client"` only on components that need state, effects, or browser APIs (`SearchBar`, `Ticker`, `LiveIndicator`). Topic and home pages stay server-rendered for SEO.
- **Tailwind v4 utilities only.** No styled-components, no raw CSS modules. Use arbitrary-value utilities (`text-[44px]`, `border-white/10`) when the value isn't in the default scale.
- **Theme tokens in `globals.css`.** Reference via `style={{ color: "var(--accent)" }}` or `bg-[var(--surface-1)]`. The full token set:
  - Color: `--background`, `--foreground`, `--foreground-2`, `--muted`, `--accent`, `--accent-hover`, `--accent-press`, `--accent-soft`, `--surface-1`, `--surface-2`
  - Source taxonomy: `--src-{kind}-{dot|bg|fg}` for kind in `wire | regional | primary | social | analysis | state`
  - Operational status: `--status-ok` (green), `--status-warn` (amber), `--status-bad` (red) — used by `StatusDot` on `/sources`. Also exposed as Tailwind `--color-status-{ok|warn|bad}` via `@theme`.
  - Fonts: Tailwind `font-sans` / `font-serif` / `font-mono` are wired through `@theme` to `--font-inter` / `--font-newsreader` / `--font-jetbrains-mono` (loaded via `next/font/google` in `layout.tsx`)
- **Type weights.** 400 / 500 / 600 only. Never 700+. Never italic in chrome.
- **Borders carry elevation.** Cards use `border border-white/10` with `hover:border-white/30`. No shadows. No gradients.
- **Metadata.** Every routable page exports `generateMetadata` (or static `metadata`). Topic and about pages set `alternates.canonical`.
- **Data fetching** goes through `lib/api.ts`. Pages don't call `fetch` directly. The client falls back to `lib/fixtures.ts` when the backend is unreachable so the site renders in dev.
- **External links.** Always `target="_blank" rel="noopener noreferrer"`.
- **Live updates.** Pages render an SSR'd initial list, then hand off to a client streamer. Topic pages use `ArticleStream` over SSE (`/stream/topic/[slug]/route.ts` proxies to the API container internally — browser stays same-origin, no CORS, no public API URL). Search uses `SearchStream` polling `/api/articles?q=` every 30s. Both dedupe new items against the SSR list by article `id`. Use `key={…}` on the parent so navigating to a new query/topic remounts the streamer cleanly.

## Voice

- Sentence case for body, page titles, topic labels (`Iran / US`).
- ALL CAPS only on eyebrows / section labels with `tracking-wider`.
- No emoji. Anywhere — product, commits, docs.
- No exclamation marks. No "AI" / "intelligence" language in v1.

## Don't

- Don't `"use client"` at the page root. Push interactivity into leaf components.
- Don't hardcode the API base URL. Use `NEXT_PUBLIC_API_BASE_URL`.
- Don't introduce a state library (Redux/Zustand) for v1. Server Components + URL state is enough.
- Don't add a parallel `--tj-*` token namespace. The production tokens are `--background` etc. — use those.
- Don't add new fonts without updating both `layout.tsx` (next/font import) and `globals.css` `@theme` block.

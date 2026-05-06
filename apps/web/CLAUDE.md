# apps/web — CLAUDE.md

Next.js 15 (App Router, TypeScript, Tailwind v4) — public site.

## Layout

```
app/
├── layout.tsx               Root layout, header/footer, fonts, global metadata
├── page.tsx                 Home — hero (title + lede + search) + Ticker + featured topics
├── globals.css              Tailwind import + theme tokens + keyframes
├── about/page.tsx           /about — what we do / don't do, source taxonomy
├── t/[topic]/page.tsx       Topic feed (SSR + ISR) — eyebrow, H1, LiveIndicator, article list
└── t/[topic]/not-found.tsx  Custom 404 voice for unknown topics

components/
├── Header.tsx               Logomark + wordmark text + nav links
├── Footer.tsx
├── Logomark.tsx             Inline SVG (six bars, rightmost in --accent)
├── SearchBar.tsx            (client) free-text → /t/<slug>
├── Ticker.tsx               (client) postage-stamp markets grid with sparklines
├── TopicTile.tsx            Featured-topic card
├── ArticleRow.tsx           Single headline row with SourcePill + meta
├── SourcePill.tsx           Color-coded badge per source kind
├── LiveIndicator.tsx        (client) pulsing dot + "Updated Xs ago"
└── EmptyState.tsx

lib/
├── api.ts                   Article/Topic types + fetcher with fixture fallback
├── topics.ts                TOPICS list, slugify, header subset
├── sources.ts               SourceKind taxonomy + labels/examples
└── fixtures.ts              Demo articles for the design preview

public/
├── logomark.svg             Six-bar logomark
├── wordmark.svg             Logomark + "Tenjin News" text
└── favicon.svg              Square favicon
```

## Conventions

- **Server Components by default.** Mark `"use client"` only on components that need state, effects, or browser APIs (`SearchBar`, `Ticker`, `LiveIndicator`). Topic and home pages stay server-rendered for SEO.
- **Tailwind v4 utilities only.** No styled-components, no raw CSS modules. Use arbitrary-value utilities (`text-[44px]`, `border-white/10`) when the value isn't in the default scale.
- **Theme tokens in `globals.css`.** Reference via `style={{ color: "var(--accent)" }}` or `bg-[var(--surface-1)]`. The full token set:
  - Color: `--background`, `--foreground`, `--foreground-2`, `--muted`, `--accent`, `--accent-hover`, `--accent-press`, `--accent-soft`, `--surface-1`, `--surface-2`
  - Source taxonomy: `--src-{kind}-{dot|bg|fg}` for kind in `wire | regional | primary | social | analysis | state`
  - Fonts: Tailwind `font-sans` / `font-serif` / `font-mono` are wired through `@theme` to `--font-inter` / `--font-newsreader` / `--font-jetbrains-mono` (loaded via `next/font/google` in `layout.tsx`)
- **Type weights.** 400 / 500 / 600 only. Never 700+. Never italic in chrome.
- **Borders carry elevation.** Cards use `border border-white/10` with `hover:border-white/30`. No shadows. No gradients.
- **Metadata.** Every routable page exports `generateMetadata` (or static `metadata`). Topic and about pages set `alternates.canonical`.
- **Data fetching** goes through `lib/api.ts`. Pages don't call `fetch` directly. The client falls back to `lib/fixtures.ts` when the backend is unreachable so the site renders in dev.
- **External links.** Always `target="_blank" rel="noopener noreferrer"`.

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

# apps/web — CLAUDE.md

Next.js 15 (App Router, TypeScript, Tailwind v4) — public site.

## Layout

```
app/
├── layout.tsx          Root layout, header, footer, global metadata
├── page.tsx            Home — featured topics
├── globals.css         Tailwind + theme tokens
└── t/[topic]/page.tsx  Topic feed page (SSR + ISR)
lib/
└── api.ts              Typed client for the FastAPI backend
```

## Conventions

- **Server Components by default.** Add `"use client"` only when you need state, effects, or browser APIs. Topic pages must be server components so SEO crawlers see content.
- **Metadata.** Every routable page exports `generateMetadata` (or static `metadata`). Topic pages set `alternates.canonical`.
- **Data fetching** goes through `lib/api.ts`. Don't `fetch` the API directly from page components — keep types and base-URL handling in one place.
- **Styling** via Tailwind v4 utility classes. Theme tokens live in `app/globals.css` as CSS variables (`--background`, `--foreground`, `--accent`); reference them as `bg-[var(--accent)]` etc. Don't add a UI kit without discussion.
- **Live updates.** Topic pages use ISR (`revalidate = 60`) for SSR snapshots and will subscribe to `${API_BASE}/stream/topic/${slug}` (SSE) from a small client component for real-time appends. SSE client component lives at `app/t/[topic]/_components/LiveFeed.tsx` (TODO).
- **Routing.** New top-level page → `app/<segment>/page.tsx`. New API client function → add to `lib/api.ts` with a return type.

## Don't

- Don't `"use client"` at the page root. Push interactivity into leaf components.
- Don't hardcode the API base URL. Use `NEXT_PUBLIC_API_BASE_URL`.
- Don't add server-side secrets to env vars prefixed with `NEXT_PUBLIC_` — they ship to the browser.
- Don't introduce a state library (Redux/Zustand) for v1. Server Components + URL state is enough.

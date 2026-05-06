import { fixtureArticles } from "./fixtures";
import { getTopicBySlug, isKnownTopic, type Topic as TopicMeta } from "./topics";
import type { SourceKind } from "./sources";

// Server-side fetches (Server Components, route handlers) prefer API_BASE_URL —
// inside docker that points at the api container directly (http://api:8000).
// Browser fetches only see NEXT_PUBLIC_API_BASE_URL since NEXT_PUBLIC_* is the
// only env namespace bundled into the client.
const API_BASE =
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export type Topic = {
  slug: string;
  label: string;
  query?: string;
  article_count_24h?: number;
};

export type Article = {
  id: string;
  url: string;
  title: string;
  outlet: string;
  source_kind: SourceKind;
  source_label: string;
  author?: string | null;
  published_at?: string | null;
  fetched_at: string;
  snippet?: string | null;
  lang?: string | null;
  topics?: string[];
  is_breaking?: boolean;
  paywall?: boolean;
};

export async function getTopic(slug: string): Promise<Topic | null> {
  const local: TopicMeta | undefined = getTopicBySlug(slug);
  if (!local) return null;
  return { slug: local.slug, label: local.label, query: local.label };
}

export async function listArticlesForTopic(
  slug: string,
  opts: { limit?: number } = {},
): Promise<Article[]> {
  const limit = opts.limit ?? 50;
  if (!isKnownTopic(slug)) return [];

  try {
    const params = new URLSearchParams({ topic: slug, limit: String(limit) });
    const res = await fetch(`${API_BASE}/articles?${params}`, {
      next: { revalidate: 30 },
    });
    if (res.ok) {
      const data = (await res.json()) as Article[];
      if (data.length > 0) return data;
    }
  } catch {
    // backend not reachable in dev — fall back to fixtures so the design renders
  }

  return fixtureArticles(slug).slice(0, limit);
}

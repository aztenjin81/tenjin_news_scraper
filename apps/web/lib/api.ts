const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Topic = {
  slug: string;
  label: string;
  query: string;
  article_count_24h?: number;
};

export type Article = {
  id: string;
  url: string;
  title: string;
  outlet: string;
  author?: string | null;
  published_at?: string | null;
  fetched_at: string;
  snippet?: string | null;
  lang?: string | null;
  topics?: string[];
};

export async function getTopic(slug: string): Promise<Topic | null> {
  const res = await fetch(`${API_BASE}/topics/${slug}`, { next: { revalidate: 60 } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`getTopic ${slug}: ${res.status}`);
  return res.json();
}

export async function listArticlesForTopic(
  slug: string,
  opts: { limit?: number; before?: string } = {},
): Promise<Article[]> {
  const params = new URLSearchParams({ topic: slug });
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.before) params.set("before", opts.before);
  const res = await fetch(`${API_BASE}/articles?${params}`, { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`listArticles: ${res.status}`);
  return res.json();
}

"use client";

import { useEffect, useState } from "react";

import type { Article } from "@/lib/api";

import { ArticleRow } from "./ArticleRow";
import { EmptyState } from "./EmptyState";

const POLL_MS = 30_000;

type Props = {
  q: string;
  initial: Article[];
};

/**
 * Renders a search result list and re-polls /api/articles?q every 30s.
 * New matches are prepended; existing rows are deduped by id.
 *
 * Free-text search isn't backed by SSE — the topic-pubsub channel only fans
 * out per registered topic, not per ad-hoc query. Polling is fine for v1.
 */
/**
 * The parent page passes `key={q}` so changing the search query unmounts and
 * remounts this component — that re-seeds `items` from `initial` cleanly,
 * without a setState-in-effect cascade.
 */
export function SearchStream({ q, initial }: Props) {
  const [items, setItems] = useState<Article[]>(initial);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!q.trim()) return;

    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch(
          `/api/articles?q=${encodeURIComponent(q)}&limit=50`,
          { cache: "no-store" },
        );
        if (!res.ok) return;
        const fresh = (await res.json()) as Article[];
        if (cancelled) return;
        setItems((prev) => {
          const seen = new Set(prev.map((a) => a.id));
          const additions = fresh.filter((a) => !seen.has(a.id));
          if (additions.length === 0) return prev;
          // Newest fresh results first (the API already orders by recency).
          return [...additions, ...prev];
        });
      } catch {
        // network hiccup — wait for the next tick
      }
    };

    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [q]);

  if (items.length === 0) return <EmptyState />;

  return (
    <ol className="m-0 list-none divide-y divide-white/10 p-0">
      {items.map((a) => (
        <ArticleRow key={a.id} article={a} />
      ))}
    </ol>
  );
}

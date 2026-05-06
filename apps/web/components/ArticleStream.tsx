"use client";

import { useEffect, useState } from "react";

import type { Article } from "@/lib/api";

import { ArticleRow } from "./ArticleRow";
import { EmptyState } from "./EmptyState";

type Props = {
  slug: string;
  initial: Article[];
};

/**
 * Renders the article list and subscribes to /stream/topic/{slug} for new
 * articles as they're persisted upstream. New rows fade in at the top.
 *
 * The browser's EventSource auto-reconnects on disconnect, so we don't need
 * any explicit retry logic here. We dedupe by article id since the SSR'd
 * initial list and the SSE stream can briefly overlap.
 */
export function ArticleStream({ slug, initial }: Props) {
  const [items, setItems] = useState<Article[]>(initial);

  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") return;

    const url = `/stream/topic/${encodeURIComponent(slug)}`;
    const es = new EventSource(url);

    const onArticle = (ev: MessageEvent<string>) => {
      try {
        const article = JSON.parse(ev.data) as Article;
        if (!article || !article.id) return;
        setItems((prev) => {
          if (prev.some((a) => a.id === article.id)) return prev;
          return [article, ...prev];
        });
      } catch {
        // ignore malformed payload — server is the source of truth
      }
    };

    es.addEventListener("article", onArticle);

    return () => {
      es.removeEventListener("article", onArticle);
      es.close();
    };
  }, [slug]);

  if (items.length === 0) return <EmptyState />;

  return (
    <ol className="m-0 list-none divide-y divide-white/10 p-0">
      {items.map((a) => (
        <ArticleRow key={a.id} article={a} />
      ))}
    </ol>
  );
}

import type { Metadata } from "next";
import Link from "next/link";

import { searchArticles } from "@/lib/api";
import { LiveIndicator } from "@/components/LiveIndicator";
import { SearchStream } from "@/components/SearchStream";

type SP = { q?: string };

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<SP>;
}): Promise<Metadata> {
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  if (!q) return { title: "Search — Tenjin News" };
  return {
    title: `${q} — Tenjin News`,
    description: `Live results for "${q}" across wires, regional outlets, primary sources, and social.`,
    robots: { index: false, follow: false },
  };
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const q = (sp.q ?? "").trim();
  const articles = q ? await searchArticles(q, { limit: 50 }) : [];
  const updatedAt = articles.length ? new Date(articles[0].fetched_at).getTime() : null;

  return (
    <div className="space-y-6">
      <div className="text-xs" style={{ color: "var(--muted)" }}>
        <Link
          href="/"
          className="transition-colors duration-150 hover:text-white"
          style={{ color: "var(--muted)" }}
        >
          Home
        </Link>
        <span className="mx-1.5">/</span>
        <span>Search</span>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <div
            className="text-xs uppercase tracking-wider"
            style={{ color: "var(--muted)" }}
          >
            Search
          </div>
          <h1
            className="mt-1 font-serif text-3xl font-semibold leading-tight sm:text-4xl"
            style={{ letterSpacing: "-0.02em" }}
          >
            {q || "Type something above"}
          </h1>
        </div>
        {q ? (
          <div className="flex flex-col items-end gap-2">
            <LiveIndicator updatedAt={updatedAt} />
            <div
              className="flex flex-wrap items-center gap-1.5 text-xs"
              style={{ color: "var(--muted)" }}
            >
              <strong className="font-medium" style={{ color: "var(--foreground-2)" }}>
                {articles.length}
              </strong>
              {articles.length === 1 ? "match" : "matches"} — refreshes every 30 s
            </div>
          </div>
        ) : null}
      </header>

      {q ? <SearchStream key={q} q={q} initial={articles} /> : null}
    </div>
  );
}

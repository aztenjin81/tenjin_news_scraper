import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTopic, listArticlesForTopic } from "@/lib/api";
import { ArticleRow } from "@/components/ArticleRow";
import { EmptyState } from "@/components/EmptyState";
import { LiveIndicator } from "@/components/LiveIndicator";

export const revalidate = 60;

type Params = { topic: string };

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { topic: slug } = await params;
  const topic = await getTopic(slug);
  if (!topic) return { title: slug };
  return {
    title: `${topic.label} — live coverage`,
    description: `Continuously updated reporting on ${topic.label}, aggregated from wires, regional outlets, primary sources, and social platforms.`,
    alternates: { canonical: `/t/${topic.slug}` },
  };
}

export default async function TopicPage({ params }: { params: Promise<Params> }) {
  const { topic: slug } = await params;
  const topic = await getTopic(slug);
  if (!topic) notFound();

  const articles = await listArticlesForTopic(slug, { limit: 50 });
  const updatedAt = articles.length
    ? new Date(articles[0].fetched_at).getTime()
    : null;

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
        <span>Topic</span>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <div
            className="text-xs uppercase tracking-wider"
            style={{ color: "var(--muted)" }}
          >
            Topic
          </div>
          <h1
            className="mt-1 font-serif text-3xl font-semibold leading-tight sm:text-4xl"
            style={{ letterSpacing: "-0.02em" }}
          >
            {topic.label}
          </h1>
        </div>
        <div className="flex flex-col items-end gap-2">
          <LiveIndicator updatedAt={updatedAt} />
          <div
            className="flex flex-wrap items-center gap-1.5 text-xs"
            style={{ color: "var(--muted)" }}
          >
            Aggregated from{" "}
            <strong className="font-medium" style={{ color: "var(--foreground-2)" }}>
              {articles.length}
            </strong>{" "}
            sources — wires, regional, primary, social
          </div>
        </div>
      </header>

      {articles.length === 0 ? (
        <EmptyState />
      ) : (
        <ol className="divide-y divide-white/10 list-none p-0 m-0">
          {articles.map((a) => (
            <ArticleRow key={a.id} article={a} />
          ))}
        </ol>
      )}
    </div>
  );
}

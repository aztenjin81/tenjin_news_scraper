import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTopic, listArticlesForTopic } from "@/lib/api";

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

  return (
    <div className="space-y-6">
      <header>
        <div className="text-xs uppercase tracking-wider text-[var(--muted)]">Topic</div>
        <h1 className="text-3xl font-semibold tracking-tight">{topic.label}</h1>
      </header>

      {articles.length === 0 ? (
        <p className="text-[var(--muted)]">No articles yet. The collector is still warming up.</p>
      ) : (
        <ol className="divide-y divide-white/10">
          {articles.map((a) => (
            <li key={a.id} className="py-4">
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lg font-medium hover:underline"
              >
                {a.title}
              </a>
              <div className="mt-1 text-xs text-[var(--muted)]">
                {a.outlet}
                {a.published_at ? ` · ${new Date(a.published_at).toUTCString()}` : ""}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

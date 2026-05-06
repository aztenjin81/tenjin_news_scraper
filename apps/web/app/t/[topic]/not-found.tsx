import Link from "next/link";
import { TOPICS } from "@/lib/topics";
import { TopicTile } from "@/components/TopicTile";

export default function TopicNotFound() {
  const suggestions = TOPICS.slice(0, 4);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-baseline gap-1.5">
        <span
          className="font-mono text-[11px]"
          style={{ color: "var(--muted)" }}
        >
          404
        </span>
        <span
          className="text-[11px] uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          No such topic
        </span>
      </div>
      <h1
        className="font-serif text-3xl font-semibold leading-tight"
        style={{ letterSpacing: "-0.02em" }}
      >
        We don&rsquo;t have a feed for that topic yet.
      </h1>
      <p
        className="mt-4 max-w-[36rem] text-[15px] leading-[1.55]"
        style={{ color: "var(--foreground-2)" }}
      >
        Tenjin only runs feeds for topics with curated source sets — that&rsquo;s how we keep the
        dedup honest and the source labels right. Try a launch vertical, or open an issue
        suggesting sources for this topic.
      </p>
      <div className="mt-8">
        <div
          className="mb-3 text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          Try instead
        </div>
        <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {suggestions.map((t) => (
            <li key={t.slug}>
              <TopicTile slug={t.slug} label={t.label} blurb={t.blurb} />
            </li>
          ))}
        </ul>
        <div className="mt-6 text-sm">
          <Link
            href="/"
            className="hover:underline"
            style={{ color: "var(--foreground)" }}
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}

import type { Metadata } from "next";
import { SearchBar } from "@/components/SearchBar";
import { SourcePill } from "@/components/SourcePill";
import { SOURCE_KINDS, SOURCE_LABELS, SOURCE_EXAMPLES } from "@/lib/sources";

export const metadata: Metadata = {
  title: "About",
  description:
    "Tenjin News is a pure aggregator. We collect, label, and link — we do not write or editorialize.",
  alternates: { canonical: "/about" },
};

const NOT_DOING: Array<[string, string]> = [
  [
    "No bodies.",
    "We display headlines, snippets, metadata, and links. Never full article bodies for outlets whose ToS forbid republication.",
  ],
  [
    "No editorializing.",
    "Source labels are honest. State media is labeled as state media. Think tanks are labeled with their funding orientation where it's a matter of public record.",
  ],
  [
    "No AI summaries in v1.",
    "LLM features are explicitly deferred to v2. We will not pretend we have them before we do.",
  ],
  ["No bypass.", "We respect robots.txt and per-source rate limits."],
];

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-2xl">
      <div
        className="text-xs uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        About
      </div>
      <h1
        className="mt-1 font-serif text-3xl font-semibold leading-tight sm:text-4xl"
        style={{ letterSpacing: "-0.02em" }}
      >
        What Tenjin News is, and is not.
      </h1>

      <section
        className="mt-8 text-base leading-[1.6]"
        style={{ color: "var(--foreground-2)" }}
      >
        <p>
          Tenjin News is a{" "}
          <strong className="font-semibold" style={{ color: "var(--foreground)" }}>
            pure aggregator
          </strong>
          . It does not write articles, it does not editorialize, and (for now) it does not
          summarize. It does one thing well:
        </p>
        <ol className="mt-3 list-decimal space-y-1 pl-6">
          <li>You give it a topic.</li>
          <li>
            It pulls from every source it knows about — wire services, major outlets, regional
            press, social platforms, government and NGO releases, think-tank publications.
          </li>
          <li>
            It deduplicates, ranks by recency and source diversity, and serves the result as a
            fast, SEO-friendly page that updates live.
          </li>
        </ol>
      </section>

      <section className="mt-10">
        <h2
          className="mb-4 text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          What we don&rsquo;t do
        </h2>
        <ul className="flex flex-col gap-3">
          {NOT_DOING.map(([title, body]) => (
            <li key={title} className="flex gap-3">
              <span
                className="mt-2 w-1 self-stretch rounded"
                style={{ background: "var(--accent)" }}
              />
              <div>
                <div className="font-semibold" style={{ color: "var(--foreground)" }}>
                  {title}
                </div>
                <div
                  className="mt-0.5 text-sm leading-[1.5]"
                  style={{ color: "var(--foreground-2)" }}
                >
                  {body}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2
          className="mb-3 text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          Source types
        </h2>
        <p
          className="mb-4 text-sm leading-[1.5]"
          style={{ color: "var(--foreground-2)" }}
        >
          Every article you see carries one of these labels.
        </p>
        <ul className="flex flex-col">
          {SOURCE_KINDS.map((k) => (
            <li
              key={k}
              className="flex items-center gap-3 border-t py-2.5"
              style={{ borderColor: "rgba(255,255,255,0.06)" }}
            >
              <SourcePill kind={k} label={SOURCE_LABELS[k]} />
              <span className="text-sm" style={{ color: "var(--muted)" }}>
                {SOURCE_EXAMPLES[k]}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2
          className="mb-3 text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          Open a feed
        </h2>
        <SearchBar />
      </section>
    </article>
  );
}

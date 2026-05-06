import { TOPICS } from "@/lib/topics";
import { TopicTile } from "@/components/TopicTile";
import { SearchBar } from "@/components/SearchBar";
import { Ticker } from "@/components/Ticker";

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="grid items-start gap-12 lg:grid-cols-[1fr_220px]">
        <div>
          <div
            className="text-xs font-medium uppercase"
            style={{ letterSpacing: "0.08em", color: "var(--muted)" }}
          >
            Live wire
          </div>
          <h1
            className="mt-2 max-w-[18ch] font-serif text-[44px] font-semibold leading-[1.05]"
            style={{ letterSpacing: "-0.02em" }}
          >
            Any topic. <span style={{ color: "var(--muted)" }}>Live.</span>
          </h1>
          <p
            className="mt-4 max-w-[44ch] text-base leading-[1.55]"
            style={{ color: "var(--foreground-2)" }}
          >
            Search any subject. Tenjin pulls a deduplicated, source-labeled feed from wires,
            regional press, primary sources, and analysis.
          </p>
          <div className="mt-6 max-w-[480px]">
            <SearchBar />
          </div>
        </div>
        <div>
          <Ticker />
        </div>
      </section>

      <section>
        <h2
          className="mb-4 text-sm font-medium uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          Featured topics
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TOPICS.map((t) => (
            <li key={t.slug}>
              <TopicTile slug={t.slug} label={t.label} blurb={t.blurb} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

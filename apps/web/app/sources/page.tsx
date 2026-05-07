import type { Metadata } from "next";

import { StatusDot } from "@/components/StatusDot";
import {
  fetchSources,
  type FeedHealth,
  type FeedHealthReport,
  type FeedStatus,
} from "@/lib/api";

export const revalidate = 30;

export const metadata: Metadata = {
  title: "Sources — Tenjin News",
  description:
    "Every feed Tenjin News tracks, with current health and last-fetch time. Coverage transparency for OSINT-leaning readers.",
  alternates: { canonical: "/sources" },
};

export default async function SourcesPage() {
  const report = await fetchSources();
  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-10">
        <p className="text-xs uppercase tracking-wider text-[var(--muted)]">
          Sources · {report.summary.total} tracked · updated{" "}
          {timeAgo(report.generated_at)}
        </p>
        <h1 className="mt-3 font-serif text-[44px] leading-tight">Sources</h1>
        <p className="mt-3 max-w-prose text-[var(--foreground-2)]">
          Every feed we track. Updated continuously. Status reflects how recently
          each source has produced content relative to its expected cadence.
        </p>
      </header>

      <SummaryCards summary={report.summary} />
      <ProblemSection
        title="Silent"
        feeds={report.feeds.filter((f) => f.status === "silent")}
        emptyMessage="Nothing silent right now."
      />
      <ProblemSection
        title="Lagging"
        feeds={report.feeds.filter((f) => f.status === "lagging")}
        emptyMessage="Nothing lagging."
      />
      <FullList feeds={report.feeds} />
    </main>
  );
}

const STATUS_VAR: Record<FeedStatus, string> = {
  ok: "var(--status-ok)",
  lagging: "var(--status-warn)",
  silent: "var(--status-bad)",
};

function SummaryCards({ summary }: { summary: FeedHealthReport["summary"] }) {
  const cards: Array<{ label: string; value: number; tone: FeedStatus }> = [
    { label: "OK", value: summary.ok, tone: "ok" },
    { label: "Lagging", value: summary.lagging, tone: "lagging" },
    { label: "Silent", value: summary.silent, tone: "silent" },
  ];
  return (
    <section className="mb-10 grid grid-cols-3 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="border px-4 py-3"
          style={{
            borderColor: `color-mix(in oklch, ${STATUS_VAR[c.tone]} 35%, transparent)`,
          }}
        >
          <div className="text-2xl font-medium" style={{ color: STATUS_VAR[c.tone] }}>
            {c.value}
          </div>
          <div className="mt-1 text-xs uppercase tracking-wider text-[var(--muted)]">
            {c.label}
          </div>
        </div>
      ))}
    </section>
  );
}

function ProblemSection({
  title,
  feeds,
  emptyMessage,
}: {
  title: string;
  feeds: FeedHealth[];
  emptyMessage: string;
}) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-xs uppercase tracking-wider text-[var(--muted)]">
        {title} · {feeds.length}
      </h2>
      {feeds.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{emptyMessage}</p>
      ) : (
        <ul className="divide-y divide-white/10 border border-white/10">
          {feeds.map((f) => (
            <FeedRow key={f.name} feed={f} />
          ))}
        </ul>
      )}
    </section>
  );
}

const KIND_ORDER = ["wire", "regional", "primary", "state", "analysis", "social"] as const;

function FullList({ feeds }: { feeds: FeedHealth[] }) {
  const grouped: Record<string, FeedHealth[]> = {};
  for (const f of feeds) {
    (grouped[f.kind] ??= []).push(f);
  }
  for (const list of Object.values(grouped)) {
    list.sort((a, b) => a.label.localeCompare(b.label));
  }

  return (
    <section>
      <h2 className="mb-3 text-xs uppercase tracking-wider text-[var(--muted)]">
        All sources · {feeds.length}
      </h2>
      <div className="space-y-6">
        {KIND_ORDER.filter((k) => grouped[k]?.length).map((kind) => (
          <div key={kind}>
            <h3 className="mb-2 text-xs uppercase tracking-wider text-[var(--muted)]">
              {kind} · {grouped[kind].length}
            </h3>
            <ul className="divide-y divide-white/10 border border-white/10">
              {grouped[kind].map((f) => (
                <FeedRow key={f.name} feed={f} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

function FeedRow({ feed }: { feed: FeedHealth }) {
  return (
    <li className="flex items-center justify-between gap-4 px-3 py-2 text-sm">
      <div className="min-w-0 flex-1 truncate">{feed.label}</div>
      <div className="text-xs text-[var(--muted)]">
        {feed.last_item_at ? timeAgo(feed.last_item_at) : "no items yet"}
      </div>
      <div className="w-20 text-right text-xs text-[var(--muted)]">
        {feed.items_24h} / 24h
      </div>
      <div className="flex w-20 items-center justify-end gap-1.5 text-xs">
        <StatusDot status={feed.status} />
        <span className="text-[var(--muted)]">{feed.status}</span>
      </div>
    </li>
  );
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

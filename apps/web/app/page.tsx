import Link from "next/link";

const FEATURED = [
  { slug: "iran-us", label: "Iran / US", blurb: "Tensions, sanctions, IRGC activity, US policy." },
  { slug: "israel-gaza", label: "Israel / Gaza", blurb: "IDF operations, humanitarian reporting." },
  { slug: "houthis-red-sea", label: "Houthis / Red Sea", blurb: "Shipping incidents, US/UK strikes." },
  { slug: "lebanon-hezbollah", label: "Lebanon / Hezbollah", blurb: "Cross-border, political." },
  { slug: "syria", label: "Syria", blurb: "Government, opposition, foreign forces." },
  { slug: "strait-of-hormuz", label: "Strait of Hormuz", blurb: "Tanker incidents, naval posture." },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Live news, organized by topic.
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--muted)]">
          Tenjin News pulls from wire services, regional outlets, primary sources, and social
          platforms — and shows you everything on a topic in one continuously updating feed.
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-[var(--muted)]">
          Featured topics
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURED.map((t) => (
            <li key={t.slug}>
              <Link
                href={`/t/${t.slug}`}
                className="block rounded-lg border border-white/10 p-4 transition hover:border-white/30"
              >
                <div className="font-medium">{t.label}</div>
                <div className="mt-1 text-sm text-[var(--muted)]">{t.blurb}</div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export type Topic = {
  slug: string;
  label: string;
  blurb: string;
};

export const TOPICS: readonly Topic[] = [
  { slug: "iran-us", label: "Iran / US", blurb: "Tensions, sanctions, IRGC activity, US policy." },
  { slug: "israel-gaza", label: "Israel / Gaza", blurb: "IDF operations, humanitarian reporting." },
  { slug: "houthis-red-sea", label: "Houthis / Red Sea", blurb: "Shipping incidents, US/UK strikes." },
  { slug: "lebanon-hezbollah", label: "Lebanon / Hezbollah", blurb: "Cross-border, political." },
  { slug: "syria", label: "Syria", blurb: "Government, opposition, foreign forces." },
  { slug: "iraq", label: "Iraq", blurb: "PMF activity, US presence, Kurdish politics." },
  { slug: "strait-of-hormuz", label: "Strait of Hormuz", blurb: "Tanker incidents, naval posture." },
] as const;

export const HEADER_TOPICS = TOPICS.slice(0, 3).map((t) => ({
  slug: t.slug,
  label: t.slug === "houthis-red-sea" ? "Houthis" : t.label,
}));

export function getTopicBySlug(slug: string): Topic | undefined {
  return TOPICS.find((t) => t.slug === slug);
}

export function isKnownTopic(slug: string): boolean {
  return TOPICS.some((t) => t.slug === slug);
}

export function slugify(query: string): string {
  return query
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}

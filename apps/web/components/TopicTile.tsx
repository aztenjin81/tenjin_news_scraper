import Link from "next/link";

type Props = {
  slug: string;
  label: string;
  blurb: string;
};

export function TopicTile({ slug, label, blurb }: Props) {
  return (
    <Link
      href={`/t/${slug}`}
      className="block rounded-lg border border-white/10 p-4 transition-colors duration-150 hover:border-white/30"
      style={{ color: "var(--foreground)" }}
    >
      <div className="font-medium">{label}</div>
      <div className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
        {blurb}
      </div>
    </Link>
  );
}

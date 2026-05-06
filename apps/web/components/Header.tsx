import Link from "next/link";
import { HEADER_TOPICS } from "@/lib/topics";
import { Logomark } from "./Logomark";

type Props = {
  current?: string | null;
};

export function Header({ current }: Props) {
  return (
    <header className="border-b border-white/10">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2.5 text-[18px] font-semibold tracking-[-0.015em] text-foreground"
          style={{ color: "var(--foreground)" }}
        >
          <Logomark />
          <span>
            Tenjin <span style={{ color: "var(--accent)" }}>News</span>
          </span>
        </Link>
        <nav className="flex gap-6 text-sm">
          {HEADER_TOPICS.map((t) => (
            <Link
              key={t.slug}
              href={`/t/${t.slug}`}
              className={`transition-colors duration-150 hover:text-white ${
                current === t.slug ? "text-foreground" : "text-[var(--muted)]"
              }`}
              style={{ color: current === t.slug ? "var(--foreground)" : "var(--muted)" }}
            >
              {t.label}
            </Link>
          ))}
          <Link
            href="/about"
            className="transition-colors duration-150 hover:text-white"
            style={{ color: current === "about" ? "var(--foreground)" : "var(--muted)" }}
          >
            About
          </Link>
        </nav>
      </div>
    </header>
  );
}

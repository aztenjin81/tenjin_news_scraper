import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Tenjin News — live news aggregation, topic-first",
    template: "%s · Tenjin News",
  },
  description:
    "Continuously updated news on Iran, Israel, Gaza, the Houthis, and the wider Middle East — pulled from wires, regional outlets, primary sources, and social platforms.",
  metadataBase: new URL("https://tenjin.news"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-white/10">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              Tenjin <span className="text-[var(--accent)]">News</span>
            </Link>
            <nav className="flex gap-6 text-sm text-[var(--muted)]">
              <Link href="/t/iran-us" className="hover:text-white">
                Iran / US
              </Link>
              <Link href="/t/israel-gaza" className="hover:text-white">
                Israel / Gaza
              </Link>
              <Link href="/t/houthis-red-sea" className="hover:text-white">
                Houthis
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        <footer className="mt-16 border-t border-white/10">
          <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-[var(--muted)]">
            Tenjin News aggregates publicly available reporting. All articles link to their original
            publishers.
          </div>
        </footer>
      </body>
    </html>
  );
}

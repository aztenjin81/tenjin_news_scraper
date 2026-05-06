import type { Article } from "@/lib/api";
import { SourcePill } from "./SourcePill";

type Props = {
  article: Article;
};

export function ArticleRow({ article }: Props) {
  const fetched = new Date(article.fetched_at);
  return (
    <li className="py-4">
      <div className="mb-1.5 flex items-center gap-2">
        <SourcePill kind={article.source_kind} label={article.source_label} />
        {article.is_breaking ? (
          <span
            className="text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--accent)" }}
          >
            New
          </span>
        ) : null}
      </div>
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[18px] font-medium hover:underline"
        style={{ color: "var(--foreground)", textWrap: "pretty" }}
      >
        {article.title}
      </a>
      <div className="mt-1.5 text-xs" style={{ color: "var(--muted)" }}>
        {article.outlet} ·{" "}
        <span className="font-mono">{fetched.toUTCString()}</span>
      </div>
    </li>
  );
}

import type { FeedStatus } from "@/lib/api";

const COLOR: Record<FeedStatus, string> = {
  ok: "var(--status-ok)",
  lagging: "var(--status-warn)",
  silent: "var(--status-bad)",
};

export function StatusDot({ status }: { status: FeedStatus }) {
  return (
    <span
      aria-label={status}
      className="inline-block h-2 w-2 rounded-full align-middle"
      style={{ backgroundColor: COLOR[status] }}
    />
  );
}

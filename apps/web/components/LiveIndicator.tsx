"use client";

import { useEffect, useState } from "react";

type Props = {
  updatedAt?: number | null;
};

export function LiveIndicator({ updatedAt }: Props) {
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  let agoLabel: string | null = null;
  if (updatedAt) {
    const ago = Math.max(1, Math.round((now - updatedAt) / 1000));
    if (ago < 60) agoLabel = `${ago} second${ago === 1 ? "" : "s"} ago`;
    else if (ago < 3600) {
      const m = Math.round(ago / 60);
      agoLabel = `${m} minute${m === 1 ? "" : "s"} ago`;
    } else {
      const h = Math.round(ago / 3600);
      agoLabel = `${h} hour${h === 1 ? "" : "s"} ago`;
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{
          background: "var(--accent)",
          animation: "tj-pulse 1.6s ease-in-out infinite",
        }}
      />
      <span
        className="text-xs font-medium uppercase tracking-wider"
        style={{ color: "var(--foreground-2)" }}
      >
        Live
      </span>
      {agoLabel ? (
        <span className="ml-1 text-xs" style={{ color: "var(--muted)" }}>
          Updated {agoLabel}
        </span>
      ) : null}
    </span>
  );
}

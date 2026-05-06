"use client";

import { useEffect, useState } from "react";

import type { Quote } from "@/lib/quotes";

const N = 24;
const POLL_MS = 60_000;

function seedSeries(px: number, vol = 0.012): number[] {
  const out: number[] = [px];
  for (let i = 1; i < N; i++) {
    const next = out[i - 1] * (1 + (Math.random() - 0.5) * vol);
    out.push(next);
  }
  out[N - 1] = px;
  return out;
}

const SEED: Quote[] = [
  { sym: "S&P", yahoo: "^GSPC", px: 5847.32, pct: 0.42, hist: [] },
  { sym: "DOW", yahoo: "^DJI", px: 42365.1, pct: -0.18, hist: [] },
  { sym: "NDX", yahoo: "^NDX", px: 20431.7, pct: 0.66, hist: [] },
  { sym: "10Y", yahoo: "^TNX", px: 4.218, pct: -0.04, suffix: "%", hist: [] },
  { sym: "VIX", yahoo: "^VIX", px: 14.62, pct: 1.93, hist: [] },
  { sym: "WTI", yahoo: "CL=F", px: 71.84, pct: -0.55, hist: [] },
  { sym: "GOLD", yahoo: "GC=F", px: 2734.5, pct: 0.31, hist: [] },
  { sym: "CXDO", yahoo: "CXDO", px: 6.41, pct: 2.71, watch: true, hist: [] },
].map((x) => ({ ...x, hist: seedSeries(x.px, x.suffix === "%" ? 0.006 : 0.012) }));

function yahooHref(yahoo: string | undefined): string | null {
  return yahoo ? `https://finance.yahoo.com/quote/${encodeURIComponent(yahoo)}` : null;
}

function fmtPx(p: number, suffix?: string): string {
  if (suffix === "%") return p.toFixed(3) + "%";
  return p >= 1000 ? p.toLocaleString("en-US", { maximumFractionDigits: 1 }) : p.toFixed(2);
}

function Sparkline({ series, up, watch }: { series: number[]; up: boolean; watch?: boolean }) {
  const W = 88;
  const H = 16;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const range = max - min || 1;
  const sx = (i: number) => (i / (series.length - 1)) * W;
  const sy = (v: number) => H - ((v - min) / range) * (H - 2) - 1;
  const path = series
    .map((v, i) => `${i === 0 ? "M" : "L"} ${sx(i).toFixed(2)} ${sy(v).toFixed(2)}`)
    .join(" ");
  const area = `${path} L ${W} ${H} L 0 ${H} Z`;
  const stroke = watch ? "var(--accent)" : up ? "#5fb682" : "#d57272";
  const fill = watch
    ? "rgba(197,48,31,0.14)"
    : up
      ? "rgba(95,182,130,0.10)"
      : "rgba(213,114,114,0.10)";
  const lastX = sx(series.length - 1);
  const lastY = sy(series[series.length - 1]);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block">
      <path d={area} fill={fill} />
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth="1"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={lastX} cy={lastY} r="1.5" fill={stroke} />
    </svg>
  );
}

export function Ticker({ initial }: { initial?: Quote[] } = {}) {
  const [items, setItems] = useState<Quote[]>(initial && initial.length > 0 ? initial : SEED);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("/api/quotes", { cache: "no-store" });
        if (!res.ok) return;
        const data = (await res.json()) as Quote[];
        if (!cancelled && Array.isArray(data) && data.length > 0) setItems(data);
      } catch {
        // upstream hiccup — keep showing the last known state
      }
    }

    // Skip the first poll if SSR already gave us fresh data.
    if (!initial || initial.length === 0) load();

    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [initial]);

  // Yahoo reports per-symbol delays (0 for indices, 15 for most US equities,
  // 10 for futures). Surface the worst case so users know what they're seeing.
  const maxDelay = items.reduce(
    (m, q) => (typeof q.delayedBy === "number" && q.delayedBy > m ? q.delayedBy : m),
    0,
  );

  return (
    <div>
      <div className="mb-2.5 flex items-baseline justify-between">
        <span
          className="text-[10px] font-medium uppercase"
          style={{ letterSpacing: "0.08em", color: "var(--muted)" }}
        >
          Markets
        </span>
        <span
          className="inline-flex items-center gap-1.5 font-mono text-[10px]"
          style={{ color: "var(--muted)" }}
        >
          <span
            className="h-[5px] w-[5px] rounded-full"
            style={{ background: "#5fb682", boxShadow: "0 0 6px #5fb682" }}
          />
          live
        </span>
      </div>
      <div
        className="grid grid-cols-2 overflow-hidden rounded-md"
        style={{
          gap: 1,
          background: "rgba(255,255,255,0.10)",
          border: "1px solid rgba(255,255,255,0.10)",
        }}
      >
        {items.map((x) => {
          const up = x.pct >= 0;
          const color = x.watch ? "var(--accent)" : up ? "#5fb682" : "#d57272";
          return (
            <div
              key={x.sym}
              title={x.watch ? `${x.sym} — on watchlist` : x.sym}
              className="relative flex min-w-0 flex-col gap-1"
              style={{ background: "var(--surface-1)", padding: "7px 9px 6px" }}
            >
              {x.watch ? (
                <span
                  className="absolute bottom-0 left-0 top-0 w-0.5"
                  style={{ background: "var(--accent)" }}
                />
              ) : null}
              <div className="flex items-baseline justify-between">
                {(() => {
                  const href = yahooHref(x.yahoo);
                  const delayLabel =
                    typeof x.delayedBy === "number" && x.delayedBy > 0
                      ? `Delayed ${x.delayedBy} min`
                      : "Real time";
                  const titleSuffix = x.watch ? " — on watchlist" : "";
                  const symStyle = {
                    letterSpacing: "0.04em",
                    color: x.watch ? "var(--accent)" : "var(--foreground-2)",
                  } as const;
                  return href ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] font-semibold hover:underline"
                      style={symStyle}
                      title={`${x.sym} on Yahoo Finance · ${delayLabel}${titleSuffix}`}
                    >
                      {x.sym}
                    </a>
                  ) : (
                    <span className="text-[10px] font-semibold" style={symStyle}>
                      {x.sym}
                    </span>
                  );
                })()}
                <span className="font-mono text-[9px] tabular-nums" style={{ color }}>
                  {up ? "+" : "−"}
                  {Math.abs(x.pct).toFixed(2)}%
                </span>
              </div>
              <Sparkline series={x.hist} up={up} watch={x.watch} />
              <div
                className="font-mono text-[10px] leading-none tabular-nums"
                style={{ color: "var(--foreground)" }}
              >
                {fmtPx(x.px, x.suffix)}
              </div>
            </div>
          );
        })}
      </div>
      <div
        className="mt-2 flex items-center justify-between font-mono text-[9px]"
        style={{ color: "var(--muted)" }}
      >
        <a
          href="https://finance.yahoo.com"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          Data: Yahoo Finance
        </a>
        <span>{maxDelay > 0 ? `Delayed up to ${maxDelay} min` : "Real time"}</span>
      </div>
    </div>
  );
}

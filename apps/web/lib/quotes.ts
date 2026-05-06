import "server-only";

export type Quote = {
  sym: string;
  px: number;
  pct: number;
  hist: number[];
  suffix?: string;
  watch?: boolean;
};

type SymbolDef = {
  sym: string;
  yahoo: string;
  suffix?: string;
  watch?: boolean;
};

const SYMBOLS: SymbolDef[] = [
  { sym: "S&P", yahoo: "^GSPC" },
  { sym: "DOW", yahoo: "^DJI" },
  { sym: "NDX", yahoo: "^NDX" },
  { sym: "10Y", yahoo: "^TNX", suffix: "%" },
  { sym: "VIX", yahoo: "^VIX" },
  { sym: "WTI", yahoo: "CL=F" },
  { sym: "GOLD", yahoo: "GC=F" },
  { sym: "CXDO", yahoo: "CXDO", watch: true },
];

const HIST_POINTS = 24;
const CACHE_TTL_MS = 30_000;

function seedHist(px: number, vol: number): number[] {
  const out: number[] = [px];
  for (let i = 1; i < HIST_POINTS; i++) {
    const next = out[i - 1] * (1 + (Math.random() - 0.5) * vol);
    out.push(next);
  }
  out[HIST_POINTS - 1] = px;
  return out;
}

const FIXTURE: Quote[] = [
  { sym: "S&P", px: 5847.32, pct: 0.42, hist: [] },
  { sym: "DOW", px: 42365.1, pct: -0.18, hist: [] },
  { sym: "NDX", px: 20431.7, pct: 0.66, hist: [] },
  { sym: "10Y", px: 4.218, pct: -0.04, suffix: "%", hist: [] },
  { sym: "VIX", px: 14.62, pct: 1.93, hist: [] },
  { sym: "WTI", px: 71.84, pct: -0.55, hist: [] },
  { sym: "GOLD", px: 2734.5, pct: 0.31, hist: [] },
  { sym: "CXDO", px: 6.41, pct: 2.71, watch: true, hist: [] },
].map((q) => ({ ...q, hist: seedHist(q.px, q.suffix === "%" ? 0.006 : 0.012) }));

let cache: { ts: number; data: Quote[] } | null = null;
let inflight: Promise<Quote[]> | null = null;

async function fetchOne(def: SymbolDef): Promise<Quote | null> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(
    def.yahoo,
  )}?interval=5m&range=1d`;
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; tenjin-news/0.1)" },
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      chart?: {
        result?: Array<{
          meta?: { regularMarketPrice?: number; chartPreviousClose?: number; previousClose?: number };
          indicators?: { quote?: Array<{ close?: Array<number | null> }> };
        }>;
      };
    };
    const result = json.chart?.result?.[0];
    if (!result?.meta) return null;
    const px = result.meta.regularMarketPrice;
    const prev = result.meta.chartPreviousClose ?? result.meta.previousClose;
    if (typeof px !== "number" || typeof prev !== "number" || prev === 0) return null;
    const pct = ((px - prev) / prev) * 100;

    const closes = result.indicators?.quote?.[0]?.close ?? [];
    const filtered = closes.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
    let hist = filtered.slice(-HIST_POINTS);
    if (hist.length === 0) hist = [px];
    if (hist[hist.length - 1] !== px) hist.push(px);
    while (hist.length < HIST_POINTS) hist.unshift(hist[0]);
    if (hist.length > HIST_POINTS) hist = hist.slice(hist.length - HIST_POINTS);

    return { sym: def.sym, px, pct, hist, suffix: def.suffix, watch: def.watch };
  } catch {
    return null;
  }
}

async function fetchAll(): Promise<Quote[]> {
  const results = await Promise.all(SYMBOLS.map(fetchOne));
  return results.filter((q): q is Quote => q !== null);
}

export async function getQuotes(): Promise<Quote[]> {
  const now = Date.now();
  if (cache && now - cache.ts < CACHE_TTL_MS) return cache.data;

  if (!inflight) {
    inflight = fetchAll().finally(() => {
      inflight = null;
    });
  }
  const fresh = await inflight;

  if (fresh.length === SYMBOLS.length) {
    cache = { ts: now, data: fresh };
    return fresh;
  }
  if (cache) return cache.data;
  return FIXTURE;
}

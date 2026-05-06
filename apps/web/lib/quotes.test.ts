import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const SYMBOL_COUNT = 8;

function yahooOk(
  px: number,
  prev: number,
  hist: (number | null)[],
  delayedBy?: number,
) {
  return {
    ok: true,
    json: async () => ({
      chart: {
        result: [
          {
            meta: {
              regularMarketPrice: px,
              chartPreviousClose: prev,
              ...(delayedBy !== undefined ? { exchangeDataDelayedBy: delayedBy } : {}),
            },
            indicators: { quote: [{ close: hist }] },
          },
        ],
      },
    }),
  };
}

describe("getQuotes", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses a well-formed Yahoo response into Quote shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(yahooOk(100, 99, [98, 99, 100])),
    );

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    expect(quotes).toHaveLength(SYMBOL_COUNT);
    const sp = quotes.find((q) => q.sym === "S&P");
    expect(sp).toBeDefined();
    expect(sp!.px).toBe(100);
    expect(sp!.pct).toBeCloseTo(((100 - 99) / 99) * 100);
    expect(sp!.hist).toHaveLength(24);
    expect(sp!.hist[sp!.hist.length - 1]).toBe(100);
  });

  it("returns FIXTURE quotes when every upstream call rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    expect(quotes).toHaveLength(SYMBOL_COUNT);
    expect(quotes.find((q) => q.sym === "S&P")!.px).toBe(5847.32);
    expect(quotes.find((q) => q.sym === "10Y")!.suffix).toBe("%");
    expect(quotes.find((q) => q.sym === "CXDO")!.watch).toBe(true);
  });

  it("returns FIXTURE on malformed Yahoo response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ wrong: "shape" }) }),
    );

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    expect(quotes.find((q) => q.sym === "S&P")!.px).toBe(5847.32);
  });

  it("returns FIXTURE when previousClose is missing or zero", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          chart: {
            result: [{ meta: { regularMarketPrice: 100 }, indicators: { quote: [{ close: [] }] } }],
          },
        }),
      }),
    );

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    expect(quotes.find((q) => q.sym === "S&P")!.px).toBe(5847.32);
  });

  it("caches successful results within the TTL window", async () => {
    const fetchMock = vi.fn().mockResolvedValue(yahooOk(100, 99, [99, 100]));
    vi.stubGlobal("fetch", fetchMock);

    const { getQuotes } = await import("./quotes");
    await getQuotes();
    const callsAfterFirst = fetchMock.mock.calls.length;
    expect(callsAfterFirst).toBe(SYMBOL_COUNT);

    await getQuotes();
    expect(fetchMock.mock.calls.length).toBe(callsAfterFirst);
  });

  it("dedupes concurrent calls into a single inflight upstream batch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(yahooOk(100, 99, [99, 100]));
    vi.stubGlobal("fetch", fetchMock);

    const { getQuotes } = await import("./quotes");
    const [a, b] = await Promise.all([getQuotes(), getQuotes()]);

    expect(a).toEqual(b);
    expect(fetchMock.mock.calls.length).toBe(SYMBOL_COUNT);
  });

  it("propagates yahoo symbol and delayedBy from upstream meta", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(yahooOk(100, 99, [99, 100], 15)));

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    const sp = quotes.find((q) => q.sym === "S&P");
    expect(sp?.yahoo).toBe("^GSPC");
    expect(sp?.delayedBy).toBe(15);
  });

  it("leaves delayedBy undefined when upstream omits exchangeDataDelayedBy", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(yahooOk(100, 99, [99, 100])));

    const { getQuotes } = await import("./quotes");
    const quotes = await getQuotes();

    const sp = quotes.find((q) => q.sym === "S&P");
    expect(sp?.delayedBy).toBeUndefined();
  });
});

/**
 * Smoke test for the /sources page module. Asserts the module exports
 * expected metadata + revalidate symbol.
 *
 * Full RSC render-snapshot tests are deferred — they require @testing-library/react
 * and a DOM env (happy-dom/jsdom) which aren't yet wired into vitest.config.ts.
 */

import { describe, expect, it, vi } from "vitest";

import { FIXTURE_SOURCES_REPORT } from "@/lib/fixtures";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchSources: vi.fn(async () => FIXTURE_SOURCES_REPORT),
  };
});

describe("/sources page module", () => {
  it("exports metadata with the right canonical and title", async () => {
    const mod = await import("./page");
    expect(mod.metadata?.title).toBe("Sources — Tenjin News");
    expect((mod.metadata?.alternates as { canonical?: string })?.canonical).toBe("/sources");
  });

  it("declares 30s ISR revalidate", async () => {
    const mod = await import("./page");
    expect(mod.revalidate).toBe(30);
  });

  it.skip("renders the silent-feed section when fetchSources returns silent feeds", async () => {
    // Deferred until DOM env + @testing-library/react are set up in vitest.config.ts.
    // Would assert that a feed with status "silent" (e.g. "IDF Spokesperson" from
    // FIXTURE_SOURCES_REPORT) appears under the "Silent" section heading.
  });
});

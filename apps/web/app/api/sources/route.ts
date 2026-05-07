/**
 * Same-origin proxy for the FastAPI /sources endpoint. Mirrors the pattern
 * used by /api/articles. Browser stays same-origin; the internal API URL
 * isn't exposed.
 */

import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UPSTREAM =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest): Promise<Response> {
  const upstream = await fetch(`${UPSTREAM}/sources`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal: req.signal,
  });

  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}

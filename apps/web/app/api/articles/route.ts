/**
 * Same-origin proxy for the FastAPI /articles endpoint. Used by client-side
 * polling (the search page polls this for new matches without leaking the
 * internal API URL or needing CORS).
 */

import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UPSTREAM =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest): Promise<Response> {
  const incoming = req.nextUrl.searchParams;

  // Only forward the query params we expose. Avoid surprising upstream params
  // leaking through.
  const out = new URLSearchParams();
  for (const key of ["q", "topic", "limit", "before"]) {
    const v = incoming.get(key);
    if (v !== null) out.set(key, v);
  }

  const upstream = await fetch(`${UPSTREAM}/articles?${out}`, {
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

/**
 * Server-side proxy for the API's SSE endpoint. The browser hits this same-
 * origin URL (`/stream/topic/iran-us`), Next.js forwards the request to the
 * api container internally over the docker network. Avoids exposing the API
 * publicly, dodges CORS entirely.
 *
 * Node runtime is required (Edge can't proxy long-lived streams reliably with
 * the current Next.js implementation).
 */

import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UPSTREAM =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> },
): Promise<Response> {
  const { slug } = await params;
  const safe = encodeURIComponent(slug);

  const upstream = await fetch(`${UPSTREAM}/stream/topic/${safe}`, {
    headers: { Accept: "text/event-stream" },
    signal: req.signal,
    cache: "no-store",
  });

  if (!upstream.ok || upstream.body === null) {
    return new Response(`upstream ${upstream.status}`, { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

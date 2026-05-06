import { NextResponse } from "next/server";

import { getQuotes } from "@/lib/quotes";

export const dynamic = "force-dynamic";

export async function GET() {
  const data = await getQuotes();
  return NextResponse.json(data, {
    headers: { "Cache-Control": "public, max-age=15, stale-while-revalidate=45" },
  });
}

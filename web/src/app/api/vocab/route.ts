import { NextRequest, NextResponse } from "next/server";
import { getVocab, lookupVocab } from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const facet = searchParams.get("facet") || undefined;
    const query = searchParams.get("query") || undefined;

    let terms;
    if (query && query.trim().length > 0) {
      terms = await lookupVocab(query.trim());
    } else {
      terms = await getVocab(facet);
    }

    return NextResponse.json({ ok: true, terms, count: terms.length });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load vocabulary" },
      { status: 500 }
    );
  }
}

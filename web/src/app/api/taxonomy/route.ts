import { NextRequest, NextResponse } from "next/server";
import { getTaxonomy } from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const entity = request.nextUrl.searchParams.get("entity") || undefined;
    return NextResponse.json({ ok: true, taxonomy: await getTaxonomy(entity) });
  } catch (error: unknown) {
    return NextResponse.json({ ok: false, error: (error as Error).message || "Failed to load taxonomy" }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { getCards } from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const search = searchParams.get("search") || undefined;
    const category = searchParams.get("category") || undefined;
    const person = searchParams.get("person") || undefined;
    const status = searchParams.get("status") || undefined;
    const limit = searchParams.get("limit") ? parseInt(searchParams.get("limit")!, 10) : 100;

    const cards = await getCards({ search, category, person, status, limit });
    return NextResponse.json({ ok: true, cards, count: cards.length });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load cards" },
      { status: 500 }
    );
  }
}

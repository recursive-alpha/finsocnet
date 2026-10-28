import { NextRequest, NextResponse } from "next/server";
import { getSources } from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const platform = searchParams.get("platform") || undefined;
    const person = searchParams.get("person") || undefined;
    const status = searchParams.get("status") || undefined;

    const sources = await getSources({ platform, person, status });
    return NextResponse.json({ ok: true, sources, count: sources.length });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load sources" },
      { status: 500 }
    );
  }
}

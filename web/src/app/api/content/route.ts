import { NextRequest, NextResponse } from "next/server";
import { getContentList } from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const platform = searchParams.get("platform") || undefined;
    const status = searchParams.get("status") || undefined;
    const person = searchParams.get("person") || undefined;
    const source = searchParams.get("source") || undefined;
    const limit = searchParams.get("limit") ? parseInt(searchParams.get("limit")!, 10) : 50;

    const contents = await getContentList({ platform, status, person, source, limit });
    return NextResponse.json({ ok: true, contents, count: contents.length });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load contents" },
      { status: 500 }
    );
  }
}

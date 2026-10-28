import { NextRequest, NextResponse } from "next/server";
import { getContent, getContentView } from "@/lib/cli";

export async function GET(
  request: NextRequest,
  segmentData: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await segmentData.params;
    const searchParams = request.nextUrl.searchParams;
    const fromSeq = searchParams.get("from_seq") ? parseInt(searchParams.get("from_seq")!, 10) : 0;
    const toSeq = searchParams.get("to_seq") ? parseInt(searchParams.get("to_seq")!, 10) : undefined;

    const [content, view] = await Promise.all([
      getContent(id),
      getContentView(id, fromSeq, toSeq).catch(() => null),
    ]);

    return NextResponse.json({ ok: true, content, view });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load content" },
      { status: 500 }
    );
  }
}

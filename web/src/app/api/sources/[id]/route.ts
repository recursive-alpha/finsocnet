import { NextRequest, NextResponse } from "next/server";
import { getSource } from "@/lib/cli";

export async function GET(
  _request: NextRequest,
  segmentData: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await segmentData.params;
    const source = await getSource(id);
    return NextResponse.json({ ok: true, source });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load source" },
      { status: 500 }
    );
  }
}

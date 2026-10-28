import { NextRequest, NextResponse } from "next/server";
import { getCard } from "@/lib/cli";

export async function GET(
  _request: NextRequest,
  segmentData: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await segmentData.params;
    const card = await getCard(id);
    return NextResponse.json({ ok: true, card });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load card" },
      { status: 500 }
    );
  }
}

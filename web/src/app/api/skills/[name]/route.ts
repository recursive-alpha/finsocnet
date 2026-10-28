import { NextRequest, NextResponse } from "next/server";
import { getSkillDetail } from "@/lib/cli";

export async function GET(
  _request: NextRequest,
  segmentData: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await segmentData.params;
    const skill = await getSkillDetail(name);
    return NextResponse.json({ ok: true, skill });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load skill details" },
      { status: 500 }
    );
  }
}

import { NextResponse } from "next/server";
import { getDoctor, getStats } from "@/lib/cli";

export async function GET() {
  try {
    const [stats, doctor] = await Promise.all([getStats(), getDoctor().catch(() => null)]);
    return NextResponse.json({ ok: true, stats, doctor });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load stats" },
      { status: 500 }
    );
  }
}

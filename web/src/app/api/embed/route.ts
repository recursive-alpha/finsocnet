import { NextResponse } from "next/server";
import { getEmbedStatus } from "@/lib/cli";

export async function GET() {
  try {
    return NextResponse.json({ ok: true, status: await getEmbedStatus() });
  } catch (error: unknown) {
    return NextResponse.json({ ok: false, error: (error as Error).message || "Failed to read embedding status" }, { status: 500 });
  }
}

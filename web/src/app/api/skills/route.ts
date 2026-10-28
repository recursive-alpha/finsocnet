import { NextResponse } from "next/server";
import { getSkills } from "@/lib/cli";

export async function GET() {
  try {
    const skills = await getSkills();
    return NextResponse.json({ ok: true, skills, count: skills.length });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load skills" },
      { status: 500 }
    );
  }
}

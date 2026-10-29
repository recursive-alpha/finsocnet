import { NextResponse } from "next/server";
import { getPersonClasses, getPersons } from "@/lib/cli";

export async function GET() {
  try {
    const [persons, classes] = await Promise.all([getPersons(), getPersonClasses().catch(() => [])]);
    return NextResponse.json({ ok: true, persons, classes });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load persons" },
      { status: 500 }
    );
  }
}

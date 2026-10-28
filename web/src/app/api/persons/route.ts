import { NextResponse } from "next/server";
import { getPersons } from "@/lib/cli";

export async function GET() {
  try {
    const persons = await getPersons();
    return NextResponse.json({ ok: true, persons });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load persons" },
      { status: 500 }
    );
  }
}

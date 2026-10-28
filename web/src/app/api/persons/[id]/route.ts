import { NextRequest, NextResponse } from "next/server";
import { getPerson, getPersonCards, getPersonRulebook } from "@/lib/cli";

export async function GET(
  _request: NextRequest,
  segmentData: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await segmentData.params;
    const [person, cardsData, rulebook] = await Promise.all([
      getPerson(id),
      getPersonCards(id).catch(() => ({ person_id: id, total: 0, categories: {} })),
      getPersonRulebook(id).catch(() => ({ markdown: "", skills: [] })),
    ]);

    return NextResponse.json({
      ok: true,
      person,
      cards: cardsData,
      rulebook,
    });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load person details" },
      { status: 500 }
    );
  }
}

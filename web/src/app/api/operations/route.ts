import { NextRequest, NextResponse } from "next/server";
import {
  getDecisions,
  getDoctor,
  getGaps,
  getQueue,
  getRuns,
} from "@/lib/cli";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tab = searchParams.get("tab") || "all";

    if (tab === "runs") {
      const runs = await getRuns(50);
      return NextResponse.json({ ok: true, runs });
    }
    if (tab === "decisions") {
      const decisions = await getDecisions(50);
      return NextResponse.json({ ok: true, decisions });
    }
    if (tab === "gaps") {
      const gaps = await getGaps();
      return NextResponse.json({ ok: true, gaps });
    }
    if (tab === "queue") {
      const queue = await getQueue();
      return NextResponse.json({ ok: true, queue });
    }
    if (tab === "doctor") {
      const doctor = await getDoctor();
      return NextResponse.json({ ok: true, doctor });
    }

    const [runs, decisions, gaps, queue, doctor] = await Promise.all([
      getRuns(20).catch(() => []),
      getDecisions(20).catch(() => []),
      getGaps().catch(() => []),
      getQueue().catch(() => []),
      getDoctor().catch(() => null),
    ]);

    return NextResponse.json({
      ok: true,
      runs,
      decisions,
      gaps,
      queue,
      doctor,
    });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to load operations data" },
      { status: 500 }
    );
  }
}

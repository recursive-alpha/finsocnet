import { NextRequest, NextResponse } from "next/server";
import { searchAll } from "@/lib/cli";

const MODES = new Set(["auto", "hybrid", "semantic", "lexical"]);
const TYPES = new Set(["cards", "contents", "persons", "skills"]);
const MULTI = ["person", "platform", "content_type", "instrument"];
const SINGLE = ["kind", "category", "domain", "horizon", "evidence_min", "min_persons", "since", "language", "status"];

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams;
  const q = (sp.get("q") || "").trim();
  if (!q) {
    return NextResponse.json({ ok: false, error: "Missing query parameter q" }, { status: 400 });
  }
  const mode = sp.get("mode") || "auto";
  if (!MODES.has(mode)) {
    return NextResponse.json({ ok: false, error: `mode must be one of ${[...MODES].join(", ")}` }, { status: 400 });
  }
  const types = (sp.get("types") || "").split(",").map((t) => t.trim()).filter(Boolean);
  if (types.some((t) => !TYPES.has(t))) {
    return NextResponse.json({ ok: false, error: `types must be a subset of ${[...TYPES].join(", ")}` }, { status: 400 });
  }
  const filters: Record<string, string | string[]> = {};
  for (const k of SINGLE) {
    const v = sp.get(k);
    if (v) filters[k] = v;
  }
  for (const k of MULTI) {
    const v = sp.getAll(k).filter(Boolean);
    if (v.length) filters[k] = v;
  }
  const limit = Math.min(Math.max(parseInt(sp.get("limit") || "40", 10) || 40, 1), 200);
  try {
    const { data, warnings } = await searchAll({ q, types, mode, limit, filters });
    return NextResponse.json({ ok: true, ...data, warnings });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json({ ok: false, error: err.message || "Search failed" }, { status: 500 });
  }
}

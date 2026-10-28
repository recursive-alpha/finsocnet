import fs from "node:fs";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";
import { getRepoRoot } from "@/lib/cli";

// Serves the pictures FinSocNet stored under data/media/ (person avatars, source icons). Nothing else on disk is reachable.
const TYPES: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

export async function GET(_request: NextRequest, segmentData: { params: Promise<{ path: string[] }> }) {
  const { path: parts } = await segmentData.params;
  // the stored path looks like "data/media/persons/<id>/<hash>.png"; accept it with or without the "data/media" prefix
  const rel = parts.join("/").replace(/^data\/media\//, "");
  const root = path.resolve(getRepoRoot(), "data", "media");
  const file = path.resolve(root, rel);
  const type = TYPES[path.extname(file).toLowerCase()];
  if (!file.startsWith(root + path.sep) || !type || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    return NextResponse.json({ ok: false, error: "Not found" }, { status: 404 });
  }
  return new NextResponse(new Uint8Array(fs.readFileSync(file)), {
    headers: { "Content-Type": type, "Cache-Control": "public, max-age=86400, immutable", "X-Content-Type-Options": "nosniff" },
  });
}

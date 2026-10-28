import { NextRequest, NextResponse } from "next/server";
import { runCliCommand } from "@/lib/cli";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const command = body.command;

    if (!command || typeof command !== "string") {
      return NextResponse.json(
        { ok: false, error: "Missing or invalid 'command' string" },
        { status: 400 }
      );
    }

    // Split args while respecting quotes
    const trimmed = command.trim();
    // Safety check: only allow finsocnet subcommands
    const parts = trimmed.startsWith("finsocnet ")
      ? trimmed.slice("finsocnet ".length).trim().split(/\s+/)
      : trimmed.split(/\s+/);

    if (parts.length === 0 || parts[0].length === 0) {
      return NextResponse.json(
        { ok: false, error: "Empty command" },
        { status: 400 }
      );
    }

    const start = Date.now();
    const result = await runCliCommand<unknown>(parts);
    const elapsed = Date.now() - start;

    return NextResponse.json({
      ...result,
      meta: {
        ...(result.meta || {}),
        api_elapsed_ms: elapsed,
      },
    });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { ok: false, error: err.message || "Failed to execute CLI command" },
      { status: 500 }
    );
  }
}

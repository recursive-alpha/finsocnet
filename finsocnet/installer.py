"""
Multi-Harness Plugin Installer for FinSocNet.
Registers /finsocnet commands, extensions, and skills across AI agent harnesses:
Claude Code, OMP, Pi, Hermes, OpenAI Codex, and OpenClaw.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent

CLAUDE_COMMAND_CONTENT = """---
description: Explore creator trading hypotheses, search strategies, and view alpha rules via FinSocNet
---

You have access to the FinSocNet intelligence and trading strategy storage engine.
Execute the `finsocnet` CLI tool via Bash based on the user's intent or arguments:

- **Search Hypotheses:** `finsocnet search "<query>"` (semantic vector search across all creators)
- **View Full Hypothesis Card:** `finsocnet view <id>` (verbatim quotes, exact timestamps, setup filters)
- **Get Creator Strategy Rulebook:** `finsocnet strategy <creator_or_strategy>` (e.g. minervini, qullamaggie, lance, smb, lewis-kelly, humbled, dante, brandt)
- **Explore Creators:** `finsocnet explore <youtube|x|reddit|medium|arxiv|annas_archive> "<target>"`
- **List Skills:** `finsocnet skills`
- **RAG Content Chunks:** `finsocnet rag "<query>"`
- **Database Stats:** `finsocnet stats`

If the user provides an argument (e.g. `/finsocnet:search breakout` or `/finsocnet minervini`), map it to the matching command above.
Format the output cleanly with creator attribution, setup conditions, holding period, and exact quotes.
"""

OMP_EXTENSION_CONTENT = """import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

interface ExtensionCommandContext {
  ui?: {
    notify?: (message: string, level?: "info" | "warning" | "error") => void;
  };
  session?: {
    sendUserMessage?: (message: string) => void;
  };
  reply?: (message: string) => void;
  send?: (msg: { role: string; content: string }) => void;
}

interface CommandOptions {
  description: string;
  handler: (args: string, ctx: ExtensionCommandContext) => Promise<void>;
}

interface HarnessAPI {
  registerCommand?: (name: string, options: CommandOptions) => void;
}

export default function (harness: unknown): void {
  if (!harness || typeof harness !== "object" || !("registerCommand" in harness)) return;
  const api = harness as HarnessAPI;
  if (typeof api.registerCommand !== "function") return;

  api.registerCommand("finsocnet", {
    description:
      "Explore creator trading strategies and hypotheses (/finsocnet search 'query', /finsocnet strategy minervini, /finsocnet stats)",
    handler: async (args: string, ctx: ExtensionCommandContext): Promise<void> => {
      const raw = (args || "").trim();
      let cmdArgs: string[] = [];

      if (raw.length === 0) {
        cmdArgs = ["stats"];
      } else {
        const match = raw.match(/(?:[^\\s"']+|"[^"]*"|'[^']*')+/g);
        if (match) {
          cmdArgs = match.map((s) => s.replace(/^['"]|['"]$/g, ""));
        } else {
          cmdArgs = raw.split(/\\s+/);
        }
      }

      try {
        const { stdout, stderr } = await execFileAsync("finsocnet", cmdArgs, {
          timeout: 45000,
        });
        const output = (stdout || stderr || "").trim();

        if (ctx.ui?.notify) {
          ctx.ui.notify("FinSocNet executed successfully", "info");
        }

        const formatted = `[FinSocNet]\\n\\`\\`\\`\\n${output}\\n\\`\\`\\``;
        if (typeof ctx.session?.sendUserMessage === "function") {
          ctx.session.sendUserMessage(formatted);
        } else if (typeof ctx.reply === "function") {
          ctx.reply(formatted);
        } else if (typeof ctx.send === "function") {
          ctx.send({ role: "user", content: formatted });
        }
      } catch (err: unknown) {
        let msg = "Unknown error occurred";
        if (err instanceof Error) {
          if ("stderr" in err && typeof err.stderr === "string" && err.stderr.length > 0) {
            msg = err.stderr;
          } else {
            msg = err.message;
          }
        }
        if (ctx.ui?.notify) {
          ctx.ui.notify(`FinSocNet error: ${msg}`, "error");
        }
      }
    },
  });
}
"""

SKILL_BRIDGE_CONTENT = """---
name: finsocnet
description: Explore, search, filter, and inspect mined trading hypotheses, creator strategies, and cross-platform market intelligence across YouTube, X, Reddit, Medium, and arXiv.
license: MIT
metadata:
  author: "finsocnet"
  version: "1.0.0"
---

# FinSocNet Skill Bridge

Allows AI agents to interface directly with the FinSocNet intelligence and trading strategy storage engine.

## Usage
Run the `finsocnet` CLI via Bash:
- `finsocnet search "<query>"`: Semantic vector search over 90+ trading hypotheses across all creators.
- `finsocnet view <id>`: View complete hypothesis card with verbatim quotes and citations.
- `finsocnet strategy <name>`: Load full strategy rulebook (e.g. minervini, qullamaggie, lewis-kelly, lance, smb, brandt, dante).
- `finsocnet explore <platform> <target>`: Explore creator content across YouTube, X, Reddit, Medium, arXiv.
- `finsocnet skills`: List available system skills vs improved strategy skills.
- `finsocnet stats`: Summary database metrics.
"""


def install_claude() -> bool:
    target_dir = HOME / ".claude" / "commands"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "finsocnet.md"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(CLAUDE_COMMAND_CONTENT)
    print(f"  ✓ Claude Code: Registered slash command at {target_file}")
    return True


def install_omp() -> bool:
    target_dir = HOME / ".omp" / "agent" / "extensions"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "finsocnet.ts"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(OMP_EXTENSION_CONTENT)
    print(f"  ✓ OMP: Installed extension at {target_file}")
    return True


def install_pi() -> bool:
    target_dir = HOME / ".pi" / "agent" / "extensions"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "finsocnet.ts"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(OMP_EXTENSION_CONTENT)
    print(f"  ✓ Pi Coding Agent: Installed extension at {target_file}")
    return True


def install_hermes() -> bool:
    target_dir = HOME / ".hermes" / "skills" / "research" / "finsocnet"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "SKILL.md"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(SKILL_BRIDGE_CONTENT)
    print(f"  ✓ Hermes: Installed skill at {target_file}")
    return True


def install_codex() -> bool:
    target_dir = HOME / ".codex" / "skills" / "finsocnet"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "SKILL.md"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(SKILL_BRIDGE_CONTENT)
    print(f"  ✓ OpenAI Codex: Installed skill at {target_file}")
    return True


def install_openclaw() -> bool:
    target_dir = HOME / ".openclaw" / "skills" / "finsocnet"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "SKILL.md"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(SKILL_BRIDGE_CONTENT)
    print(f"  ✓ OpenClaw: Installed skill at {target_file}")
    return True


def install_agents_shared() -> bool:
    target_dir = HOME / ".agents" / "skills" / "finsocnet"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "SKILL.md"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(SKILL_BRIDGE_CONTENT)
    print(f"  ✓ Agent Skills: Installed shared skill at {target_file}")
    return True


HARNESS_INSTALLERS = {
    "claude": install_claude,
    "omp": install_omp,
    "pi": install_pi,
    "hermes": install_hermes,
    "codex": install_codex,
    "openclaw": install_openclaw,
    "shared": install_agents_shared,
}


def install_harness(name: str = "all") -> None:
    target = name.lower().strip()
    print(f"Installing FinSocNet harness integration for: '{target}'...")

    if target == "all":
        install_agents_shared()
        for h_name, fn in HARNESS_INSTALLERS.items():
            if h_name != "shared":
                try:
                    fn()
                except Exception as e:
                    print(f"  [WARN] Failed to install {h_name}: {e}", file=sys.stderr)
        print("\nAll AI harness integrations successfully registered!")
    elif target in HARNESS_INSTALLERS:
        HARNESS_INSTALLERS[target]()
        print(f"\nFinSocNet successfully installed for {target}!")
    else:
        print(f"Unknown harness: {target}. Available options: {', '.join(list(HARNESS_INSTALLERS.keys()) + ['all'])}")

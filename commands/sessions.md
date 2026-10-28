---
description: "Show browser session status per platform"
argument-hint: ""
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Run `uv run --project $FINSOCNET_HOME .agents/skills/session-bridge/scripts/session_bridge.py status`. For any platform that is logged out or at a checkpoint, give the user the re-export steps: `finsocnet session export && finsocnet session push` on their machine.

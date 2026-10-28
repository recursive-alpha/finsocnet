---
name: agent-browser
description: Start, check and debug the single Chrome browser that all FinSocNet platform skills attach to over CDP on the remote host — dedicated profile with imported sessions, headed under Xvfb, optional SOCKS egress through the user's home IP, per-platform rate budgets and checkpoint detection, plus a VNC view for solving security checks by hand. Use when a script exits with BROWSER_UNAVAILABLE (code 7), before any browser-based platform work, when the user asks to open or screenshot a page in the agent browser, or to check egress IP and budgets.
license: MIT
compatibility: Remote Linux host with Google Chrome/Chromium/Brave, Xvfb (when no DISPLAY), optional x11vnc + noVNC; FinSocNet repository with uv and Playwright (CDP client only).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "3"
  spec: docs/spec/04-sessions-browser.md
---

# Agent Browser

One Chrome per remote host, profile `data/browser-profile/`, DevTools on `127.0.0.1:9222`. Every platform script attaches with `connect_over_cdp` and opens its own page in the existing context. No script launches a browser or creates a new context — that would lose the imported sessions and look like a bot.

## Commands

```bash
uv run .agents/skills/agent-browser/scripts/agent_browser.py start [--proxy socks5://127.0.0.1:1080] [--match-ua]
uv run .agents/skills/agent-browser/scripts/agent_browser.py status     # pid, CDP ok, Chrome version, proxy, egress IP, open pages, budgets used today
uv run .agents/skills/agent-browser/scripts/agent_browser.py open <url> [--screenshot data/screenshots/x.png]
uv run .agents/skills/agent-browser/scripts/agent_browser.py stop
uv run .agents/skills/agent-browser/scripts/agent_browser.py vnc [--stop]   # noVNC on 127.0.0.1:6080 for manual checks
```

`start` is idempotent (returns `already_running` if CDP answers), starts Xvfb on `XVFB_DISPLAY` when there is no `DISPLAY`, launches Chrome without automation flags, then runs `session_bridge.py reapply`.

## Procedure: a script failed with code 7 (`BROWSER_UNAVAILABLE`)

1. `agent_browser.py status`.
2. Not running → `agent_browser.py start`, then retry the script once.
3. Running but proxy unreachable (hint says so) → the user's SSH tunnel dropped: ask the user to restart `ssh -N -R 1080 <user@host>`, or start without `--proxy`.
4. Still failing → `kb lesson add --skill agent-browser --kind script_bug …` and report.

## Budgets and checkpoints

- Every navigation/API request is charged to the platform budget in `config/budgets.yaml` (per minute/hour/day). Exhausted → exit 4 `BUDGET_EXHAUSTED` with `retry_after_sec`: defer the queue item, do not retry sooner.
- After every navigation the page is checked against `config/platforms.yaml` logged-out and checkpoint patterns. Match → exit 3: follow `session-bridge` "exit code 3" procedure.
- Scripts pause a random human-like delay between actions (per platform `min_delay_ms`..`max_delay_ms`).

## Debugging a platform page

`agent_browser.py open <url> --screenshot data/screenshots/<name>.png` and look at the screenshot (read the PNG). Record selector or endpoint changes in that platform skill's `references/platform_notes.md` and add a lesson (`--kind platform_change`).

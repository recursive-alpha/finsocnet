---
name: discord-explorer
description: Read Discord servers on any topic — list servers and channels, read text, forum and announcement channels and threads by day, search a server, and store messages as FinSocNet content — either through the agent browser with the user's imported Discord session (read-only) or with an official bot in servers the user administers. Use for discord.com/channels links, discord.gg invites, "what do people in <server> say about …".
license: MIT
compatibility: FinSocNet repository; user mode needs agent-browser and an imported discord.com session; bot mode needs DISCORD_BOT_TOKEN for servers where the bot was added.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "6"
  spec: specs/05-platform-skills.md
---

# Discord Explorer

**Risk:** automating a personal Discord account breaks Discord's terms and can get it banned. Prefer a secondary account and bot mode where possible; keep the budget low. This skill is enabled only after the user accepts the risk (SPEC §9 Q2). The script never sends its own API requests with the user token: it scrolls the web app and reads the responses the app itself loads.

## When to use

- Discord server/channel/message links, community knowledge in trading Discords.

## Before you start

- User accepted the risk; agent browser running; `session_bridge.py status --platform discord` logged_in (user mode).
- Session `discord` (user mode): check with `uv run .agents/skills/session-bridge/scripts/session_bridge.py status --platform discord`. Never ask the user for passwords or tokens; sessions come only from session-bridge.

## Commands

```bash
S=.agents/skills/discord-explorer/scripts/discord.py
uv run $S list servers
uv run $S list <guild_id>
uv run $S list <channel_id> [--since D]
uv run $S search "<query>" --guild <guild_id> [--limit 100]
uv run $S fetch <channel_id> --since D [--until D] [--max-messages 2000] [--mode user|bot] [--ingest]
uv run $S fetch <message link> [--ingest]
```

| Command | Returns |
|---|---|
| `list servers` | guilds from the sidebar |
| `list <guild_id>` | text, forum and announcement channels |
| `list <channel_id>` | day windows available |
| `search "<query>" --guild <guild_id>` | in-app search results |
| `fetch <channel_id> --since D` | one ContentRecord per channel per UTC day |
| `fetch <message link>` | the day window containing it |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill discord-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. New server: `list servers` → `list <guild>` → pick channels with trading content (education, trade-ideas, recaps) → `fetch <channel> --since <30-90 days> --ingest --run R` → market-idea-miner per day window.
3. Refetching the same day appends new messages (incremental).
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `discord:<channel_id>:<YYYY-MM-DD>` (threads: thread id) |
| source id | `discord:server:<guild_id>`, `discord:channel:<channel_id>` |
| content_type | `chat_window` |
| segments | each message `kind=message {message_id, reply_to?}`, author `{handle, platform_user_id}`; embeds' text appended; attachments → media |
| persons | authors become `private_source` persons unless public elsewhere |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill discord-explorer --kind script_bug …` with the error, then report |

## Notes

- Budget `discord` in config/budgets.yaml.
- Message links: `https://discord.com/channels/<guild>/<channel>/<message_id>`.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.

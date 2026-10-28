---
name: session-bridge
description: Move the user's logged-in browser sessions from their local machine to the remote FinSocNet host — export cookies (all domains), localStorage and optional history into an age-encrypted bundle, push it, import it into the agent browser profile, verify logins per platform, re-apply after restarts, and purge. Use when a platform says login required or checkpoint, when setting up a new remote host, when the user mentions cookies, sessions, logging in, a folder of exported cookies, or /finsocnet:sessions. Never handles passwords.
license: MIT
compatibility: Remote side needs the FinSocNet repository, the agent-browser skill and pyrage; local side needs `finsocnet` installed with the `local` extra (install.sh --local) and ssh/scp access to the remote.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "3"
  spec: docs/spec/04-sessions-browser.md
---

# Session Bridge

## Secret rules (always)

- Never print, log, store in the DB, write to `data/work/`, or commit cookie values, tokens or localStorage values. Only domain names, counts and expiry dates may be shown.
- Never type credentials into a website. Logins happen in the user's own local browser.
- Secrets on the remote live only in `data/browser-profile/`, `data/sessions/store.age` (encrypted), `data/sessions/cookies.txt` and `data/sessions/storage/*.json` (chmod 600).

## One-time setup

Remote (you can run these):
```bash
uv run .agents/skills/session-bridge/scripts/session_bridge.py keygen        # prints recipient age1…
uv run .agents/skills/agent-browser/scripts/agent_browser.py start
```
Local (tell the user to run these on their machine):
```bash
curl -fsSL https://raw.githubusercontent.com/recursive-alpha/finsocnet/main/install.sh | bash -s -- --local
finsocnet session init-local --recipient <age1…> --remote <user@host> --remote-path <repo path>
```

## Getting sessions onto the remote

Tell the user to run on their machine (after logging in to the sites in their normal browser):
```bash
finsocnet session export          # all domains; --browser chrome|brave|edge|firefox, --profile NAME, --history, --exclude DOMAIN
finsocnet session push            # scp to the remote and import
```
Or, if the user dropped files into `data/sessions/inbox/` (cookies.txt, Cookie-Editor JSON, Playwright storage_state, Firefox profile):
```bash
uv run .agents/skills/session-bridge/scripts/session_bridge.py import data/sessions/inbox/ --run <R>
```
Imports include **all** cookie domains (nothing ignored); the user can exclude domains at export time.

## Commands (remote)

| Command | Result |
|---|---|
| `session_bridge.py import <bundle-or-folder> --run R` | cookies + localStorage injected into the agent browser; metadata in `browser_sessions`; history → `history_entries`; inbox deleted; status table |
| `session_bridge.py status [--platform P]` | per platform: domain, cookie count, earliest expiry, login_state |
| `session_bridge.py verify [--platform P \| --all]` | runs login probes from `config/platforms.yaml` |
| `session_bridge.py reapply` | re-inject session cookies + localStorage (run automatically by `agent_browser.py start`) |
| `session_bridge.py purge [--domain D … \| --all] --run R` | remove cookies from the profile, store, cookies.txt and metadata — confirm with the user first |

## When a platform script exits with code 3 (`LOGIN_REQUIRED` / `CHECKPOINT`)

1. Stop work on that platform for this run; `kb queue update <id> --status deferred --retry-after 3600 --run R`.
2. `session_bridge.py verify --platform <p>`.
3. Tell the user once per platform:
   ```
   <Platform> on the remote host is <logged out | blocked by a security check>.
   On your machine: open <platform URL>, log in (complete any check), then run:
     finsocnet session export && finsocnet session push
   ```
4. Continue with other platforms.
5. If the check can only be solved from the remote IP: `agent_browser.py vnc`, and tell the user to run `ssh -L 6080:127.0.0.1:6080 <user@host>` and open http://localhost:6080 to solve it by hand.

## Tips to give the user

- Platforms tie sessions to IP (Google, Facebook, LinkedIn, Instagram). The remote browser can use the user's home IP: on their machine `ssh -N -R 1080 <user@host>`; on the remote start the browser with `FINSOCNET_PROXY=socks5://127.0.0.1:1080`.
- For Discord, Facebook, LinkedIn and Instagram, a secondary account is safer: automating a personal account can get it banned.

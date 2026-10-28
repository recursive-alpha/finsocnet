# Sessions and the agent browser

FinSocNet runs on a server. Some platforms (X, Facebook, LinkedIn, Instagram, Discord, Seeking Alpha, paid newsletters…) need a logged-in browser. **You log in on your own machine; the server never sees a password.** The session is shipped encrypted, and every browser-based skill uses one agent Chrome.

```
YOUR MACHINE                               SERVER
log in to the sites in your browser
finsocnet session export  ──encrypted──►   session_bridge.py import
finsocnet session push                      └► agent_browser.py start  (one Chrome, CDP 127.0.0.1:9222)
                                                 └► every platform skill attaches to it
```

## One-time setup

```bash
# server
uv run .agents/skills/session-bridge/scripts/session_bridge.py keygen              # prints the age recipient (age1…)
uv run .agents/skills/agent-browser/scripts/agent_browser.py start                 # add --headless without a display

# your machine
finsocnet session init-local --recipient age1… --remote me@host --remote-path /srv/finsocnet
```

## Every time a session expires

```bash
# your machine: log in to the site in your normal browser first
finsocnet session export && finsocnet session push
# server (done for you by the push, or by hand)
uv run .agents/skills/session-bridge/scripts/session_bridge.py import
uv run .agents/skills/session-bridge/scripts/session_bridge.py verify --all         # probes each platform's login (config/platforms.yaml)
```

When a skill exits with code **3** (`LOGIN_REQUIRED` or `CHECKPOINT`) it stops that platform and tells you which export to redo. Never retry in a loop.

## What is and is not stored

- Bundles are encrypted with [age](https://age-encryption.org) to the server's key; the private key stays outside the repository (`AGE_IDENTITY_FILE`).
- Cookie values and tokens are never printed, logged or put in the database or in `.env`; a test checks for leaks. The database only knows which platforms are logged in.
- There is no password login anywhere (ADR-005). All domains in the browser export are imported; `--exclude` drops some (bank, mail).

## One browser, enforced budgets

No skill launches its own browser: they attach over CDP to the agent Chrome (ADR-006; a test fails on `chromium.launch`). Page loads pause like a person, respect per-platform budgets (`config/budgets.yaml`) and stop on checkpoints (captcha, "unusual activity"). On Linux without a display: `agent_browser.py start --headless`, or `vnc` to solve a check by hand once.

## Risks

Automating a user account on Discord, Facebook, LinkedIn or Instagram can violate their terms and get the account restricted. Use a secondary account, keep the strict budgets, do not run those adapters on your main account. See [`specs/README.md`](../specs/README.md) §9 (open questions) and [`specs/04-sessions-browser.md`](../specs/04-sessions-browser.md).

Reddit note: from some server networks Reddit blocks its JSON endpoints; the adapter then falls back to the RSS feeds (post plus first comments, flagged `extra.partial`).

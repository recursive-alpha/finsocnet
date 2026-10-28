# 04 — Session Bridge and Agent Browser

FinSocNet runs on a remote host. The user's logged-in browser is on their local machine. This document specifies how sessions move from local to remote (ADR-005) and how all browsing happens through one agent browser (ADR-006).

---

## 1. Topology

```
LOCAL (user's machine)                                   REMOTE (FinSocNet host)
  finsocnet (installed by install.sh)                      repo checkout + uv env
  ├─ session init-local --recipient age1… --remote …       ├─ session_bridge.py keygen       (once)
  ├─ session export  → bundle (age-encrypted)              ├─ session_bridge.py import       (each push)
  ├─ session push    → scp → remote:data/sessions/inbox/   ├─ agent_browser.py start|stop|status|reapply
  └─ ssh -R 1080 … (optional egress tunnel)                └─ Chrome (Xvfb), CDP 127.0.0.1:9222,
                                                              profile data/browser-profile/
```

---

## 2. One-Time Setup

### 2.1 Remote

```bash
uv run .agents/skills/session-bridge/scripts/session_bridge.py keygen
# → writes AGE_IDENTITY_FILE (default ~/.config/finsocnet/age_identity.txt, chmod 600)
# → prints the recipient public key: age1qxyz…
uv run .agents/skills/agent-browser/scripts/agent_browser.py start
```

### 2.2 Local

```bash
curl -fsSL https://raw.githubusercontent.com/recursive-alpha/finsocnet/main/install.sh | bash   # installs `finsocnet`
finsocnet session init-local --recipient age1qxyz… --remote user@host --remote-path /srv/finsocnet
# → ~/.config/finsocnet/remote.toml  {recipient, remote, remote_path}
```

---

## 3. Export (local) — `finsocnet session export`

```
finsocnet session export [--browser chrome|chromium|brave|edge|firefox] [--profile NAME]
                         [--from-dir PATH] [--history] [--exclude DOMAIN …] [--out FILE]
finsocnet session push [FILE]          # default: newest bundle in ~/.local/share/finsocnet/bundles/
```

### 3.1 Inputs and readers (`finsocnet/core/sessions/formats.py`, `export_local.py`)

| Input | Detection | Reader |
|---|---|---|
| Chrome-family profile | `<profile>/Cookies` (or `Network/Cookies`) SQLite | Method A (preferred): copy the profile's `Cookies`, `Local Storage/leveldb`, `Preferences` into a temp user-data-dir, launch the **same** local Chrome binary on it with `--remote-debugging-port`, read cookies via CDP `Storage.getCookies` (Chrome decrypts) and localStorage via `DOMStorage`. Method B (fallback): `rookiepy` decryption. Method C: ask the user to export with an extension (§3.1 rows below). The tool tries A → B → C and reports which worked. |
| Firefox profile | `cookies.sqlite`, `webappsstore.sqlite` / `storage/default/*/ls/data.sqlite` | direct SQLite read (not encrypted) |
| Netscape `cookies.txt` | header `# Netscape HTTP Cookie File` or 7 tab-separated fields | parser |
| Cookie-Editor / EditThisCookie JSON | array of objects with `name`, `value`, `domain` | parser (map `expirationDate` → `expires`, `sameSite` values) |
| Playwright `storage_state` | object with `cookies` and `origins` | parser |
| HAR file | `log.entries` | read `Set-Cookie`/`Cookie` headers (last resort) |
| History | Chrome `History` (`urls` table), Firefox `places.sqlite` (`moz_places`) | only with `--history`; copy file first (it is locked while the browser runs) |

`--from-dir` scans a folder recursively, detects every file by content (not extension), merges all cookies (newest `expires` wins for the same `(name, domain, path)`), and reports per file what was found.

**Spike required in Phase 3:** verify method A on Linux, macOS and Windows (Chrome ≥ 127 app-bound encryption). Record results in `docs/spec/04-sessions-browser.md` §9.

### 3.2 Bundle format

`b-<UTC>-<hex>.bundle` = age-encrypted (to the remote recipient) `tar.gz` containing:

```
manifest.json
cookies.json            # [{name, value, domain, path, expires, httpOnly, secure, sameSite, partitionKey?}]
local_storage.json      # {"https://discord.com": {"key": "value", …}, …}
history.jsonl           # optional: {"url","title","visit_count","last_visit_at"} per line
```

`manifest.json`:
```json
{
  "bundle_id": "b-20261028091500-a1f3",
  "created_at": "2026-10-28T09:15:00Z",
  "source": {"browser": "chrome", "version": "141.0.7390.54", "profile": "Default", "os": "windows",
             "user_agent": "Mozilla/5.0 …", "locale": "en-US", "timezone": "Asia/Ho_Chi_Minh", "method": "A"},
  "domains": {"x.com": {"cookies": 14, "earliest_expiry": "2026-11-20T00:00:00Z", "local_storage": false}, "…": {}},
  "excluded_domains": [],
  "counts": {"cookies": 1832, "domains": 211, "local_storage_origins": 37, "history_entries": 0}
}
```

Rules: **all domains are included** (ADR-007) unless the user passes `--exclude`. The export prints only the manifest summary. The plaintext tarball is built in memory or in a temp dir that is deleted; only the encrypted file is written to disk.

### 3.3 Push

`session push` copies the bundle with `scp` to `<remote>:<remote_path>/data/sessions/inbox/` and, if `ssh` works, runs `uv run …/session_bridge.py import data/sessions/inbox/<file>` remotely and prints the status table.

---

## 4. Import (remote) — `session_bridge.py`

```
session_bridge.py keygen
session_bridge.py import <bundle-or-folder> [--run R]
session_bridge.py status [--platform P]                 # table from browser_sessions + live cookie counts via CDP
session_bridge.py verify [--platform P|--all]           # runs login probes (§4.3)
session_bridge.py reapply                               # re-inject session cookies + localStorage (on browser start)
session_bridge.py purge [--domain D …|--all] [--run R]  # removes cookies from profile + store + metadata
```

### 4.1 Import steps

1. Input is a `.bundle` (decrypt with `AGE_IDENTITY_FILE`) **or** a plain folder dropped in `data/sessions/inbox/` (parsed with the same `formats.py` readers; a folder may contain a Chrome/Firefox profile copied from the user's machine only if the remote can decrypt it — Firefox yes, Chrome usually no → error with hint "export locally instead").
2. Normalize cookies; drop expired ones (count them in the result).
3. Require the agent browser (`BROWSER_UNAVAILABLE` otherwise). Inject cookies with CDP `Storage.setCookies` on the browser target. Inject localStorage per origin: open a blank page, navigate to the origin root with request interception that returns an empty 200 page, `DOMStorage.setDOMStorageItem` / `localStorage.setItem` for each key, close the page.
4. Persist an encrypted copy of the normalized cookies + localStorage to `data/sessions/store.age` (encrypted to the host's own recipient). Needed because session cookies (no `expires`) are lost when Chrome restarts; `reapply` re-injects them.
5. Write `data/sessions/cookies.txt` (Netscape) for yt-dlp and `data/sessions/storage/<platform>.json` (Playwright format) for each platform in `config/platforms.yaml`; `chmod 600`.
6. Upsert `browser_sessions` rows (metadata only) for every domain; `history.jsonl` → `history_entries` (`triage = 'pending'`).
7. Securely delete the inbox input (overwrite + unlink for files; remove folders).
8. Run `verify --all` for known platforms; return the status table.

Output (`data`):
```json
{"bundle_id": "b-20261028091500-a1f3", "cookies_imported": 1790, "cookies_expired_dropped": 42,
 "domains": 211, "local_storage_origins": 37, "history_entries": 0,
 "platforms": [{"platform": "x", "domain": "x.com", "cookies": 14, "earliest_expiry": "2026-11-20T00:00:00Z", "login_state": "logged_in"},
               {"platform": "facebook", "domain": "facebook.com", "cookies": 9, "earliest_expiry": "2027-01-02T00:00:00Z", "login_state": "checkpoint"}]}
```

### 4.2 Secret handling (tested, see 00 §10)

- No command prints cookie values, localStorage values, or tokens; `status` prints counts and dates only.
- Values never enter `knowledge.db`, logs, `data/work/`, exceptions, or git.
- Files with secrets: `data/sessions/store.age` (encrypted), `cookies.txt` and `storage/*.json` (plaintext, `chmod 600`, regenerated on import, removed by `purge`), `data/browser-profile/` (Chrome's own storage).
- The age identity file lives outside the repo (`~/.config/finsocnet/`).

### 4.3 Login probes (`config/platforms.yaml`)

```yaml
x:
  domains: [x.com, twitter.com]
  session_cookies: [auth_token, ct0]          # presence check (verify names during implementation)
  probe_url: https://x.com/home
  logged_out_url_patterns: ["/i/flow/login", "/login"]
  checkpoint_patterns: ["/account/access", "captcha", "unusual activity"]
reddit:
  domains: [reddit.com]
  session_cookies: [reddit_session, token_v2]
  probe_url: https://www.reddit.com/api/me.json
  logged_in_json_path: data.name
facebook:
  domains: [facebook.com]
  session_cookies: [c_user, xs]
  probe_url: https://www.facebook.com/me
  logged_out_url_patterns: ["/login"]
  checkpoint_patterns: ["/checkpoint/", "confirm your identity"]
google:
  domains: [google.com, youtube.com]
  session_cookies: [SID, __Secure-3PSID]
  probe_url: https://myaccount.google.com/
  logged_out_url_patterns: ["accounts.google.com/v3/signin", "ServiceLogin"]
  checkpoint_patterns: ["/sorry/", "unusual traffic"]
medium:      {domains: [medium.com], session_cookies: [sid, uid], probe_url: https://medium.com/me/stats, logged_out_url_patterns: ["/m/signin"]}
substack:    {domains: [substack.com], session_cookies: [substack.sid], probe_url: https://substack.com/api/v1/user/profile/self}
discord:     {domains: [discord.com], local_storage_keys: [token], probe_url: https://discord.com/channels/@me, logged_out_url_patterns: ["/login"]}
telegram:    {domains: [web.telegram.org], local_storage_keys: [user_auth], probe_url: https://web.telegram.org/k/}
linkedin:    {domains: [linkedin.com], session_cookies: [li_at], probe_url: https://www.linkedin.com/feed/, logged_out_url_patterns: ["/login", "/authwall"], checkpoint_patterns: ["/checkpoint/"]}
instagram:   {domains: [instagram.com], session_cookies: [sessionid], probe_url: https://www.instagram.com/accounts/edit/, logged_out_url_patterns: ["/accounts/login"]}
tradingview: {domains: [tradingview.com], session_cookies: [sessionid], probe_url: https://www.tradingview.com/u/}
seekingalpha: {domains: [seekingalpha.com], probe_url: https://seekingalpha.com/account/profile, checkpoint_patterns: ["px-captcha", "Press & Hold"]}
tiktok:      {domains: [tiktok.com], session_cookies: [sessionid], probe_url: https://www.tiktok.com/setting}
threads:     {domains: [threads.net, threads.com], session_cookies: [sessionid], probe_url: https://www.threads.net/}
stocktwits:  {domains: [stocktwits.com], probe_url: https://stocktwits.com/settings}
```

Probe result: `logged_in` if session cookies are present AND the probe URL does not redirect to a logged-out pattern AND no checkpoint pattern is found in URL or visible text; `checkpoint` if a checkpoint pattern matches; else `logged_out`. Cookie names marked "verify" must be checked against the real site during implementation and corrected here.

---

## 5. Login Expired → Re-Export Protocol

Any script that detects a logged-out or checkpoint page exits with code 3 (`LOGIN_REQUIRED` / `CHECKPOINT`). The agent then:

1. Stops all work on that platform for this run. `kb queue update <id> --status deferred --retry-after 3600` for the current item.
2. Updates metadata: `session_bridge.py verify --platform <p>` (sets `login_state`).
3. Tells the user, once per platform per run:
   ```
   <Platform> on the remote host is <logged out | blocked by a security check>.
   On your machine: open <platform URL>, log in (and complete any check), then run:
     finsocnet session export && finsocnet session push
   ```
4. Continues with other platforms. `kb queue next` skips platforms whose `login_state` ≠ `logged_in` when they require a session.

Optional, for checkpoints that must be solved on the remote IP: `agent_browser.py vnc` starts `x11vnc` + noVNC on `127.0.0.1:6080`; the user runs `ssh -L 6080:127.0.0.1:6080 user@host` and opens `http://localhost:6080` to solve it by hand. The agent never types credentials.

---

## 6. Agent Browser (`agent-browser`)

### 6.1 Commands

```
agent_browser.py start [--headless] [--proxy URL]   # starts Xvfb (if no DISPLAY) + Chrome; then session_bridge reapply
agent_browser.py stop
agent_browser.py status                              # pid, CDP reachable, version, proxy, open pages, budgets today
agent_browser.py open <url> [--screenshot]           # debug helper: open, wait, print title/url, optional screenshot
agent_browser.py vnc [--stop]
```

### 6.2 Launch flags (normative)

```
$CHROME_BIN
  --user-data-dir=$BROWSER_PROFILE_DIR
  --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222
  --no-first-run --no-default-browser-check
  --window-size=1366,900 --lang=<manifest locale or en-US>
  [--proxy-server=$FINSOCNET_PROXY]
env: DISPLAY=$XVFB_DISPLAY (when started by us), TZ=<manifest timezone>
```
Forbidden: `--enable-automation`, `--headless` (unless `--headless` is passed explicitly for debugging), `--disable-blink-features` tricks, user-agent override (unless `session export --match-ua` was used and `agent_browser start --match-ua` is passed).

PID file: `data/browser-profile/.finsocnet.pid`. `start` is idempotent: if CDP answers, return `already_running`.

### 6.3 `finsocnet.core.browser`

```python
def attach() -> tuple[Playwright, Browser, BrowserContext]:
    """connect_over_cdp(CDP_URL); return browser.contexts[0] (the persistent profile context).
    Raises BrowserUnavailable (exit 7) if CDP is unreachable. Never creates a new context."""

@contextmanager
def page(platform: str, *, block: tuple[str, ...] = ("media", "font")) -> Iterator[Page]:
    """Charge budget(platform) (exit 4 if exhausted); open a new page in contexts[0]; optional resource blocking;
    after every navigation run check_page(platform, page); always close the page on exit."""

def check_page(platform: str, page: Page) -> None:
    """Apply config/platforms.yaml logged_out_url_patterns / checkpoint_patterns to page.url and visible text
    (first 5000 chars). Raise LoginRequired or Checkpoint (exit 3)."""

def capture_json(page: Page, url_pattern: str) -> list[dict]:
    """Collect JSON bodies of responses whose URL matches url_pattern while the caller scrolls/navigates.
    Used by X (GraphQL), Discord (REST), Facebook (GraphQL), TradingView."""

def human_pause(platform: str) -> None:
    """Sleep a random duration between budgets[platform].min_delay_ms and max_delay_ms."""

def scroll(page: Page, *, max_scrolls: int, until: Callable[[], bool] | None = None) -> int:
    """Scroll with human_pause between steps; stop at max_scrolls, when until() is true, or when height stops growing."""
```

Concurrency: several scripts may attach at once; each uses its own page. A platform-level file lock (`data/browser-profile/.lock-<platform>`) ensures one script per platform at a time.

---

## 7. Budgets (`config/budgets.yaml`, `finsocnet.core.budgets`)

```yaml
default:      {per_minute: 20, per_hour: 300, per_day: 3000, min_delay_ms: 800,  max_delay_ms: 2500}
google:       {per_minute: 3,  per_hour: 30,  per_day: 200,  min_delay_ms: 4000, max_delay_ms: 12000}
x:            {per_minute: 6,  per_hour: 150, per_day: 1200, min_delay_ms: 2000, max_delay_ms: 6000}
facebook:     {per_minute: 4,  per_hour: 60,  per_day: 400,  min_delay_ms: 3000, max_delay_ms: 9000}
linkedin:     {per_minute: 2,  per_hour: 20,  per_day: 100,  min_delay_ms: 5000, max_delay_ms: 15000}
instagram:    {per_minute: 3,  per_hour: 40,  per_day: 250,  min_delay_ms: 4000, max_delay_ms: 10000}
discord:      {per_minute: 6,  per_hour: 120, per_day: 1000, min_delay_ms: 2000, max_delay_ms: 5000}
reddit:       {per_minute: 10, per_hour: 300, per_day: 3000, min_delay_ms: 1000, max_delay_ms: 3000}
seekingalpha: {per_minute: 2,  per_hour: 30,  per_day: 150,  min_delay_ms: 5000, max_delay_ms: 12000}
tiktok:       {per_minute: 4,  per_hour: 60,  per_day: 400,  min_delay_ms: 3000, max_delay_ms: 8000}
stackexchange: {per_minute: 25, per_hour: 1000, per_day: 9000, min_delay_ms: 100, max_delay_ms: 300}
sec:          {per_minute: 300, per_hour: 10000, per_day: 50000, min_delay_ms: 110, max_delay_ms: 200}
```

- A "unit" = one page navigation or one API request.
- `charge(platform)` increments `budget_usage` for minute/hour/day windows in one transaction; if any window is full → `BUDGET_EXHAUSTED` with `retry_after_sec` = seconds to the window end.
- APIs with their own limits (Stack Exchange `backoff`, HTTP 429 `Retry-After`) are honoured on top: `RATE_LIMITED` with that delay.

---

## 8. Network Egress (optional, recommended for Google/Facebook/LinkedIn/Instagram)

Sessions are bound to IP by some platforms. To make the remote browser use the user's home IP:

```bash
# on the local machine (keep running)
ssh -N -R 1080 user@remote-host          # OpenSSH ≥ 7.6: dynamic SOCKS proxy on the remote's 127.0.0.1:1080
# on the remote
FINSOCNET_PROXY=socks5://127.0.0.1:1080 agent_browser.py start
```

`agent_browser.py status` shows the egress IP (fetches `https://api.ipify.org` through the browser). If the tunnel drops, Chrome requests fail → scripts exit 7 with hint "proxy unreachable".

---

## 9. Implementation Notes (Phase 3 spike, 2026-10-28)

| Item | Result |
|---|---|
| Method A on Linux (Chromium 156, `--password-store=basic`) | **Works.** A copy of `Default/Cookies` (+ `Local State`) opened by the same binary with a debugging port returns the decrypted cookie (tested with a cookie written by another Chrome run). With a desktop keyring (`Chrome Safe Storage`) it depends on D-Bus being reachable; not verified. |
| Method A on macOS | _not verified_ (no machine available); expected to need the login keychain to be unlocked |
| Method A on Windows (app-bound encryption, Chrome ≥ 127) | _not verified_; expected to fail for cookies written by recent Chrome, then method B (`rookiepy`) or method C (extension export) |
| Verified cookie names per platform | _not verified live_ (needs the user's accounts); the names in `config/platforms.yaml` follow this spec and are marked "verify" |
| Discord / Telegram localStorage keys | _not verified live_ |
| Chrome without a keyring | **Hangs on the first cookie operation** (D-Bus lookup). `agent_browser.py start` therefore passes `--password-store=basic --use-mock-keychain` on Linux. |
| Cookie persistence | Chrome writes cookies to disk about 30 s after they are set; session cookies never. `session_bridge.py reapply` (run on every `agent_browser.py start`) restores them from `data/sessions/store.age`. |
| `Storage.setCookies` / `Storage.getCookies` / `Storage.clearCookies` | **Work** on the browser-target session (`browser.new_browser_cdp_session()`), once the keyring hang above is avoided; this is what `CdpSink` uses. |

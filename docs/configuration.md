# Configuration

No credentials anywhere: logins go through the [session bridge](sessions.md). Copy `.env.example` to `.env` to change defaults.

## Environment (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `KNOWLEDGE_DB_PATH` | `data/knowledge.db` | the one database (relative to the repository root) |
| `FINSOCNET_ROOT` | the checkout | relocate the repository (tests, scratch roots) |
| `FINSOCNET_RUN_ID` | — | run id used by write commands when `--run` is absent |
| `FINSOCNET_LOG_LEVEL` | `INFO` | stderr log level |
| `FINSOCNET_UI` | — | `1` = terminal view instead of JSON for every command |
| `FINSOCNET_EMBED_PROVIDER`, `FINSOCNET_EMBED_MODEL` | from `config/embedding.yaml` | `fastembed` or `hashing` (offline); model id |
| `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE` | large-v3-turbo / auto / int8 | local speech-to-text (the only other model scripts run) |
| `CDP_URL`, `BROWSER_PROFILE_DIR`, `CHROME_BIN`, `XVFB_DISPLAY` | `http://127.0.0.1:9222`, `data/browser-profile` | the agent browser |
| `FINSOCNET_PROXY` | — | egress proxy for HTTP and the browser (e.g. a reverse SSH tunnel to your home IP) |
| `AGE_IDENTITY_FILE` | `~/.config/finsocnet/age_identity.txt` | server private key for session bundles, outside the repo |
| `SEC_USER_AGENT`, `STACKEXCHANGE_KEY`, `GITHUB_TOKEN`, `OPENALEX_MAILTO` | — | optional: only raise public rate limits |
| `FINSOCNET_ALLOW_NPX`, `FINSOCNET_REA_VERSION`, `FINSOCNET_REA_TIMEOUT` | `0`, `6.8.0`, `300` | [REA](reverse-anything.md) |

## `config/`

| File | Content |
|---|---|
| `platforms.yaml` | per platform: domains, whether a session is required, cookie names, login probe, checkpoint patterns, `refresh_hours` |
| `budgets.yaml` | per platform: `per_minute / per_hour / per_day` and `min/max_delay_ms`; `default` applies to unknown platforms; `probe` is the site-probe budget |
| `forums.yaml` | forums the adapter already knows (any other forum is detected from the page) |
| `embedding.yaml` | provider, model, query/doc prefix, batch size, cache dir ([Search](search.md)) |
| `sites/<name>.yaml` | recipes of your own platforms ([Exploring](exploring.md#new-sites-platform-skill-builder)); the file name is the platform name |
| `skills.lock.json` | third-party skills installed through `skill-installer`, with source commit and file hashes |

## Data layout (`data/`, git-ignored)

`knowledge.db` (+ WAL) · `backups/` · `raw/` (original responses, so content can be re-parsed) · `records/` (ContentRecords) · `media/` (`persons/`, `sources/` pictures) · `models/` (embedding model) · `work/<run>/` (agent scratch files) · `sessions/`, `browser-profile/` · `skill-staging/`, `skill-backups/` · `inbox/documents/`.

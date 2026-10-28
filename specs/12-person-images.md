# 12 — Person images

Code: `finsocnet/core/media.py`, `persons.image_add|image_fetch|image_list`, `kb person avatar …`, `profile --ingest`. Migrations `004` (`person_images`, `persons.avatar_*`) and `005` (`sources.avatar_*`). Skill: `person-matcher` §Pictures.

## 1. Data

| Where | Fields |
|---|---|
| `persons` | `avatar_url` (a hint, may be stale), `avatar_path`, `avatar_sha256`, `avatar_mime`, `avatar_fetched_at` — the primary picture |
| `person_images` | every stored picture: `kind` (`avatar` `banner` `photo` `logo`), `platform`, `source_url`, `path`, `sha256`, `mime`, `width`, `height`, `bytes`, `fetched_at`, `run_id`; unique on `(person_id, sha256)` |
| `sources` | `avatar_url`, `avatar_path`, `avatar_sha256` — channel / subreddit / profile icon, filled by `profile --ingest` |
| files | `data/media/persons/<person id>/<sha256[:20]>.<ext>`, `data/media/sources/…` (git-ignored, content-addressed) |

## 2. Rules

- **Only real images, identified by bytes.** Magic number and Pillow must agree (png, jpeg, gif, webp); 200 B ≤ size ≤ 8 MB (rejects tracking pixels and HTML error pages); the server's content type is only a pre-filter.
- The first avatar becomes primary; later ones do not replace it unless `--primary`. Non-avatar kinds never set the primary slot.
- A merge moves images to the target and fills its avatar if empty (`person merge`).
- Only pictures the person publishes themselves (profile pictures, official site images). No search-engine image scraping, no private photos, nothing attached when the handle↔person match is uncertain.
- Downloads go through `core.http` (budgets, retries, exit-code mapping). A failed download is a warning / listed error, never a failed profile.

## 3. Commands and flow

`kb person avatar add --person P (--url U | --file F) [--kind K] [--platform X] [--primary]` · `kb person avatar fetch --person P` (downloads `persons.avatar_url` and the `avatar_url` of every source linked to the person; reports per-URL errors) · `kb person avatar list --person P`.

Flow (person-matcher): for each handle `profile <handle> --ingest --run R` (stores the source avatar) → `kb source upsert` with `person_id` → `kb person avatar fetch`. `avatar_url` is returned by the profile of: bluesky, github, podcast, rss, reddit (users and subreddits), stackexchange, stocktwits, substack, telegram, x, youtube, and (from `og:image`) medium, tradingview, facebook, threads, instagram, linkedin, seekingalpha.

## 4. UI

`GET /api/media/<path>` (web) serves only files under `data/media/` with an image extension; `Avatar` shows the picture or initials.

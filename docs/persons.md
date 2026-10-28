# People and pictures

Knowledge belongs to **people**, not channels. A person has one canonical record; handles on many platforms are aliases; every citation says who said it and in which role.

## Who counts, and discovering them first

A person is anyone who publishes knowledge about markets or economics: **traders, portfolio managers, investors, CEOs and founders, economists, central bankers and regulators, professors and researchers, analysts, strategists, authors, journalists, educators**. Each person has a `profession`, an `affiliation`, `domains`, a `homepage`, a one-sentence `relevance` (the evidence they are in scope) and `external_ids` (OpenAlex, ORCID, Google Scholar, SSRN, Wikipedia). Skill [`people-discoverer`](../.agents/skills/people-discoverer/SKILL.md) finds and creates them *before* their content is crawled, links their channels, accounts, sites and papers, and queues them; `finsocnet kb person list --profession academic` filters. Design: [`specs/16`](../specs/16-people-first-discovery.md); scholar databases (Google Scholar, SSRN authors, RePEc, ORCID) are the next step.

## Matching

Skill [`person-matcher`](../.agents/skills/person-matcher/SKILL.md): from the title, description, source owner and first segments of a content the agent finds the cast (owner, host, guest, author, commenter), searches candidates (`kb person candidates --name … --handle … --platform …`), and confirms or creates persons and appearances (`kb person upsert`, `alias add`, `appearance add`). Uncertain matches wait in a review queue (`finsocnet persons review`). Speakers in interviews are attributed segment by segment.

```bash
finsocnet kb person list --ui
finsocnet kb person get tom-dante --ui          # profile, aliases, images, sources, appearances
finsocnet kb person cards tom-dante             # active cards he is cited in, by category
finsocnet kb person merge --from dup-id --into tom-dante     # moves aliases, citations, images; history kept
```

## Rulebooks

Skill [`person-skill-synthesizer`](../.agents/skills/person-skill-synthesizer/SKILL.md) rewrites a person's cards into seven sections (overview, setup and screening, entry and execution, trade management, risk and sizing, psychology and review, checklists) stored in `person_skills`. They live in the database, **not** in skill folders:

```bash
finsocnet strategy tom-dante                    # rendered markdown
finsocnet kb skill get tom-dante --render markdown
```

`/finsocnet:strategy <person>` and `/finsocnet:compare a,b <topic>` use them.

## Avatars and other images

Each person can have pictures stored **as files** (`data/media/persons/<id>/<hash>.<ext>`, content-addressed) with rows in `person_images`, and a primary avatar in `persons.avatar_path` (`avatar_sha256`, `avatar_mime`, `avatar_fetched_at`). Channel and profile icons of sources are kept too (`sources.avatar_*`).

```bash
# 1. a platform profile gives the picture URL; --ingest stores the source and downloads its icon
uv run .agents/skills/youtube-extractor/scripts/youtube.py profile UCLn8btkaQ5hVWNMt9TxQtsQ --ingest --run $R
# 2. link the source to the person (the agent does this when matching)
echo '{"id": "youtube:channel:UCLn8btkaQ5hVWNMt9TxQtsQ", "person_id": "kristjan-qullamaggie"}' > src.json
finsocnet kb source upsert --file src.json --run $R
# 3. download every known avatar URL of the person (person field + linked sources); errors are listed per URL
finsocnet kb person avatar fetch --person kristjan-qullamaggie --run $R
# manual: a URL or a file the user gave you; --primary replaces the main picture; --kind banner|photo|logo
finsocnet kb person avatar add --person kristjan-qullamaggie --url https://example.org/me.png --platform web --run $R
finsocnet kb person avatar list --person kristjan-qullamaggie
```

Rules: only real images (checked by bytes, 200 B – 8 MB, png/jpeg/gif/webp); the first avatar becomes primary; only pictures the person publishes themselves; nothing is attached when the match between a handle and the person is uncertain (a company channel is not its founder). Profile pictures are returned by the profiles of YouTube, X, Reddit, Bluesky, GitHub, Stack Exchange, StockTwits, Substack, Telegram, podcasts, RSS and (through `og:image`) Medium, TradingView, Facebook, Threads, Instagram, LinkedIn and Seeking Alpha. The web UI shows them ([Web UI](web-ui.md)). Details: [`specs/12-person-images.md`](../specs/12-person-images.md).

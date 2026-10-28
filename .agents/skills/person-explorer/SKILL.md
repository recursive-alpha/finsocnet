---
name: person-explorer
description: Start from one person's profile URL (YouTube channel, X, LinkedIn, Substack, personal site, Google Scholar, GitHub, podcast page — any platform) and complete the knowledge about them on your own — identify who they are, create or match the person, find and verify all their other places, list everything they published (long and short videos, posts, papers, episodes), fetch and mine the most important content into Knowledge Cards, follow new links they reveal, and report what is complete and what is missing. Use for "explore this person <url>", "here is a trader's profile, find everything", "start from their channel/website and discover the rest", or when `finsocnet explore add <url> --person` queued a profile.
license: MIT
compatibility: FinSocNet repository (finsocnet kb CLI); every platform skill; person-matcher, person-profiler, market-idea-miner; agent browser and session-bridge for platforms that need a session.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "9"
  spec: specs/16-people-first-discovery.md
---

# Person Explorer

The user gives you **one URL of a person**. You turn it into a complete, verified picture of that person and their knowledge. You are the conductor: the work is done by the skills you call, and every step is judged by you. There is no person-specific script and no per-person skill folder.

## When it starts

- `finsocnet explore add <profile url> --person` queues the profile (`action=profile`, `origin_ref=person-explore`); `source-explorer` hands such an item to this skill.
- Or the user simply says "explore this person: <url>".

## Procedure

1. `uv run finsocnet kb run start --skill person-explorer --goal "explore person from <url>" --harness <h> --model <m>` → `R`. Pass `--run R` to every write below.
2. **Resolve the seed.** Use `source-explorer/references/dispatch.md` (URL pattern → platform skill). Run that skill's `profile "<url>" --ingest --run R`:
   - social/video/newsletter profile → name, handle, bio, description, links, picture, follower scale;
   - personal site, Scholar, GitHub, Wikipedia or any other page → `web-reader` (`web.py fetch <url>`), `research.py profile`, `github.py profile`.
   Exit 3 → that seed needs a session: tell the user which export to redo (`session-bridge`) and continue with the places that work.
3. **Who is this, and are they in scope?** `person-matcher` (`kb person candidates --name … --handle … --context …`). Known person → continue with that id. Unknown → apply the gate of `people-discoverer` (one sentence of `relevance` about markets, investing or economics + one verifiable fact). Out of scope → say so, store the source only as a source (`kb source upsert`, no `person_id`), end the run. In scope → `kb person upsert` (id, profession, affiliation, domains, relevance, homepage, external_ids you saw on a page) and link the seed source (`person_id`, appearance `role: owner`, evidence = what proved it: the profile is the URL the user gave, plus the facts you read).
4. **Complete the profile** with `person-profiler` for this person id (same run `R`): official site first, then each platform, matching with evidence (confirmed ≥ 0.9, needs_review 0.5–0.89, rejected not stored). The seed URL itself is stored as a link with `confidence ≥ 0.95` and `evidence: "profile URL given by the user"`. Pictures: `kb person avatar fetch --person <id> --run R`.
5. **Discover everything they published.** For every confirmed content place (channel, feed, newsletter, podcast, blog, GitHub, papers author page) run the platform skill's `list --catalog --run R` (YouTube: `--tab all` for long videos, shorts and streams). Catalog items are stored as `metadata_only` contents, so the whole inventory exists after one call. Report the totals per platform: `kb stats` or `kb content list --source <id>`.
6. **Fetch and mine what they are known for first.** Rank the inventory (views/likes, pinned or "popular", titles that teach a method, playlists, long-form over clips) and pick a budget (default: top 10 per place, then more only if the first ones produced cards). For each: platform `fetch "<url>" --ingest --run R` → skill `market-idea-miner` → `knowledge-dedup` → `kb card commit` → `kb content done`. Transcripts blocked or no text? leave the content `metadata_only`, record the reason in the run stats and go on; never loop on a blocked platform. Everything not fetched yet goes to the queue: `kb queue add --origin person_crosslink --origin-ref person:<id> --action fetch|crawl_source --priority 0.4..0.7`.
7. **Follow what you learned.** New people (guests, co-authors, mentors the person names) and new places appear while reading. Places of the same person: back to step 4 (at most **two rounds**). Other people: `kb queue add --origin mention` (never create them from one mention); an in-scope guest with their own channel can become the next `person-explorer` run.
8. **Synthesize.** With ≥ 5 cards attributed to the person: `person-skill-synthesizer` (rulebook), then `kb embed sync` so search sees the new cards.
9. **Report** to the user in plain words: who the person is (profession, affiliation), the links found (confirmed vs needs review, with the evidence of the surprising ones), inventory per platform (listed / fetched / mined), cards created, what is blocked and why (session, bot check, no transcript), what is queued next. `kb run end --run R --outcome success|partial --stats '{"person": "<id>", "links_confirmed": n, "links_needs_review": n, "listed": n, "fetched": n, "cards": n, "blocked": ["youtube: bot check"], "queued": n}'`.

## Completeness checklist (state each as done / not possible + why)

profile fields · picture · official site · social accounts · newsletter · podcast · papers/scholar ids · inventory per content place · top content mined · rulebook · queue for the rest.

## Rules

- Everything in `person-profiler` applies: public professional information only, no guessed URLs, evidence for every link, no passwords or cookies, uncertain means `needs_review`.
- The seed is trusted as **the user's pointer**, not as proof that the account is the person it claims: still read it (an impersonator or fan page is possible) and say so in the evidence.
- Stay within budgets and respect exit codes: 3 → stop that platform and name the export to redo; 4 → `deferred` with `retry_after_sec`; 7 → `agent-browser start` once.
- Do not mine in the same run what another run already holds: `kb content claim` refuses; `kb seen check` first.
- Never write scraping code for a platform that has a skill; if a skill is missing, use `platform-skill-builder` and tell the user.

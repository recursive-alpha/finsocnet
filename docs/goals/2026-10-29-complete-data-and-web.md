# Goal (2026-10-29): a trustworthy web, a complete CLI, full and diverse data

Archived as given by the user (lightly edited for spelling), with the state of each part. Update the status when you change it.

> The previous run stopped because other processes used up the CPUs. Check again, run again, but update and start the web first; review the display CSS/JS. Clicking a person shows the detail, the overview is good, but the knowledge card shows unexpected popups. Review and test all displays for better UX.
>
> This is a harness with skills first: complete the CLI before spawning oh-my-pi agents. All skill access to the database (read / update / remove) goes through CLI commands; do not write scripts that access the database.
>
> People classification: set a static classification with an "other" class. (Follow-up: the same for knowledge cards, content, sources, skills, vocabulary, …: review all and update.)
>
> Why does "Appearances in content" show nothing / raise page-not-found? If possible, add links to all mentioned resources (website, identifiers, …).
>
> After all of that, delegate to oh-my-pi sub-agents to refill all data. Make sure we can explore all people, all data and all their knowledge from articles, newspapers, books, talks, videos: as much as possible. The exploration skill must guide the agent in detail. Free to design and update, but the goal must be archived.

## Parts and status

| # | Part | Where | Status |
|---|---|---|---|
| 1 | Web rebuilt and started first; pages reviewed in a real browser (Playwright script, outside the repo) | `docker compose up -d --build`; screenshots of persons, person tabs, cards, dashboard | done |
| 2 | Unexpected card popups: a card opened from a person used to stack a second popup on top and leave the person popup behind. Now one popup frame; the card opens **inside** the person popup with a back button; Escape closes only the top layer | `web/src/components/ModalFrame.tsx`, `CardModal.tsx` (`CardDetail`), `PersonModal.tsx` | done |
| 3 | Person popup: tab bar was clipped; fixed (`shrink-0`) | `PersonModal.tsx` | done |
| 4 | Complete CLI: every read/update/remove through `kb`: `query`, `schema`, `taxonomy`, `person classes|coverage|remove|alias remove|appearance list|remove|link remove`, `person list` filters, `content list` filters, `source list` filters, `queue remove`, `card list` filters | `finsocnet/core/{dbtools,classes,taxonomy,persons,content,queue,kb_cli}.py`, `docs/agent-guide.md` §6b, skill `knowledge-db` | done |
| 5 | Static classifications with a catch-all: people (16 classes, `other`), card kind/category/domain/evidence/horizon/action, content type/status/platform, source platform/kind/status, vocabulary facets, skill groups, rulebook categories; web filters read them from `kb taxonomy`; a test ties them to the schemas/migrations/skills folder; `kb audit` lists values outside the lists | `finsocnet/core/taxonomy.py`, `tests/unit/test_taxonomy.py`, `web/src/components/FilterChips.tsx` | done |
| 6 | Appearances in content: now opens the stored text inside the profile (internal view) with a separate button for the original page; the old external links pointed at URLs invented by earlier agents, which gave 404 | `PersonModal.tsx` (Sources tab) | done |
| 7 | Links to every mentioned resource: homepage, identifiers (OpenAlex, ORCID, Scholar, SSRN, RePEc, Wikipedia, Wikidata, …) and platform aliases become links | `web/src/lib/identifiers.ts`, `PersonModal.tsx` | done |
| 8 | Exploration skill with detailed guidance: `person-explorer` step 6b (knowledge sweep) + `references/knowledge-sources.md` (per content type and per class: articles, newspapers, books, talks, videos, podcasts, papers, letters, social) driven by `kb person coverage` (gaps = to-do) | `.agents/skills/person-explorer/` | done |
| 9 | Delegate to oh-my-pi agents to refill the data (fewer at a time: CPU is shared), review every result with `kb audit`, fix what is wrong | see `specs/09-checklist.md` §2.9d and the run log in the final report | in progress |

## Done means (measurable)

`kb audit` shows: no active card without a fetched source; every person has the profile fields and an avatar from pages that were opened; people with 0 cards go down; `kb person coverage` gaps are empty or accounted for (blocked / searched without result); sources with no person go down; no values outside the static classifications.

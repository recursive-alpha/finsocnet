# Legacy (v1) — read-only

Everything here was removed from `.agents/skills/` by the v2 spec (`specs/README.md` §5.3). It is kept, unchanged, because Phase 2 of `specs/08-phases.md` converts it into Knowledge Cards and `person_skills` rows. Do not add to it and do not load these folders as skills.

| Folder | What it is | Converted by | Delete when |
|---|---|---|---|
| `person-skills/` | 9 per-person rulebook folders (`SKILL.md` + `references/*.md`) | Phase 2, task 3 (agent conversion → cards → `person-skill-synthesizer`) | user approves `specs/improvements/legacy-conversion.md` |
| `meta-skills/hypothesis-miner` | v1 miner | replaced by `market-idea-miner` | Phase 2 done |
| `meta-skills/skill-curator`, `meta-skills/user-skill-synthesizer` | v1 folder generators | replaced by `person-skill-synthesizer` | Phase 2 done |
| `meta-skills/skill-explorer` | Chroma skill search | replaced by `knowledge-search`, `person-skills-explorer` (ADR-001) | Phase 2 done |
| `scripts/` | v1 batch pipelines that build person folders | not converted | Phase 2 done |
| `references/` | v1 docs: password login guide, Playwright launch guide, v1 DB schema | superseded by `specs/04`, `specs/01` | Phase 0 done |

`finsocnet strategy <name>` reads `legacy/person-skills/` until Phase 2 replaces it with `kb skill get`.

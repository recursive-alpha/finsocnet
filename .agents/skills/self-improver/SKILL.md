---
name: self-improver
description: Improve FinSocNet from its own run history — read failed runs, lessons, user feedback, open knowledge gaps, validation error patterns, vocabulary health and evaluation scores; apply safe reversible data fixes (merge/split/retire cards, fix speaker attribution, vocabulary aliases and merges); re-check past dedup decisions blind; and propose instruction, few-shot or script changes only as git branches with before/after eval results for the user to merge. Use for /finsocnet:improve, scheduled maintenance, or when the user says "improve the skills", "why does search miss …", "clean up duplicates", "review lessons".
license: MIT
compatibility: Requires the FinSocNet repository with git, the finsocnet kb and eval CLIs.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: planned
  phase: "5"
  spec: docs/spec/06-explore-improve-eval.md
---

# Self-Improver

> **Status: planned — built in Phase 5.**

## Hard limits

- Never commit to `main` and never merge your own branches. Instruction, few-shot, vocabulary-seed and script changes go on `self-improve/<YYYYMMDD>-<topic>` for the user to review.
- Never edit eval golden cases in the same branch as the instructions they test.
- Never edit installed third-party skills (entries in `config/skills.lock.json`); record lessons about them and tell the user, who can change them upstream.
- Data fixes must be reversible: use `kb card merge|retire|update` (they snapshot to `card_history`) with `--reason "<lesson/feedback id>: …"`.

## Procedure (one run)

1. `kb run start --skill self-improver --goal "maintenance" …` → `R`.
2. **Collect signals**
   - `kb run list --since 7d` (outcome ≠ success) and their `errors_json` grouped by error code
   - `kb lesson list --status open`, `kb feedback list --status open`, `kb gap list --status open`
   - vocabulary health: `kb vocab list` → near-duplicate keys/labels, aliases claimed by two terms, unused terms > 90 days, frequent card aliases missing from the vocabulary
3. **Re-dedup sweep**: `kb decision list --reviewed none` → sample 30 (mix of decision types). For each, rebuild the input from `new_card_json` and the candidates as they were (`kb card get <id> --history`), decide again without looking at the stored decision, then compare:
   - agree → `kb decision review <id> --verdict agreed --run R`
   - disagree → reason with both rationales; if the new decision is better → `--verdict overturned --note "…"`, apply the data fix (merge, split = retire + re-commit, add link), and `kb lesson add --skill knowledge-dedup --kind few_shot …`
   - report the agreement rate in run stats; < 85% → lesson for `knowledge-dedup` few-shots.
4. **Apply data fixes** directly (cards, citations, persons, vocabulary). Mark feedback handled: `kb feedback handle <id> --run R`.
5. **Group the remaining lessons** by skill and kind. For each topic worth changing:
   ```
   git switch -c self-improve/<YYYYMMDD>-<topic>
   finsocnet eval run --all   → data/work/R/eval_before.json   (follow its prepare → produce → score steps)
   <edit SKILL.md / references/*.md / script>
   finsocnet eval run --all   → data/work/R/eval_after.json
   ```
   Keep the change only if the target set improves and no other set drops by more than 2 points. Write `docs/improvements/<YYYYMMDD>-<topic>.md` (lessons, change, before/after table), commit, `kb lesson update <ids> --status proposed --ref <branch> --run R`, switch back to the original branch.
6. `kb run end --run R --outcome success --stats '{"data_fixes": N, "proposals": N, "dedup_agreement": 0.0}'`.
7. Report to the user: data fixes applied (with undo hint `kb card undo --history-id …`), branches proposed with their before/after tables, open questions.

## Cadence

After every 20 mining runs or daily, whichever comes first; on demand via `/finsocnet:improve`.

## Eval targets (from `docs/spec/06-explore-improve-eval.md` §3.4)

transform validity 100% · transform recall ≥ 0.80 · precision ≥ 0.75 · dedup accuracy ≥ 0.85 · wrong-merge rate ≤ 0.03 · search recall@10 ≥ 0.80 · attribution accuracy ≥ 0.85.

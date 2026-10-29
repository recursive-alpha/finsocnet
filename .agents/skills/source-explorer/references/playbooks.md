# Playbooks: what "explore X" means, step by step

Read `docs/agent-guide.md` first (rules, definition of done). Each playbook ends with `kb audit` numbers in your report. `S="uv run finsocnet kb"`; every write has `--run R`.

## 1. A list of people ("Nobel laureates", "100 central bankers", "channels that teach trading")

1. Get the list from a page you opened: `web.py fetch <list url>` (Wikipedia list, official site). Keep the rows as a plan file in the temp dir, not in the repo.
2. For each person, **one at a time** (newest to oldest when asked): `person candidates` → gate (`relevance` + one fact from a page you read) → `person upsert` → `person-explorer` steps 2–9. Do not create 100 stubs first and "fill later".
3. Content for scholars and officials: their own text. Order of preference: lecture/speech pages (nobelprize.org lectures, central bank speech archives, BIS), their working papers (`research.py search "<name>"`, `research.py fetch`), their lecture notes on their university site (`web.py fetch`, `document.py fetch` for PDFs), books (playbook 3), talks (`youtube.py search "<name> lecture" --type video`).
4. Progress is `kb audit` (people with an active card / total), not the plan file.

## 2. A channel, newsletter, podcast, feed

`profile <target> --ingest` → create/attach the person (person-explorer) → `list <target> --catalog [--tab all]` → rank the inventory → `fetch --ingest` the top 10 (popular + teaching) → mine → queue the rest. Blocked transcripts: record the reason, queue, move on.

## 3. Books (Anna's Archive and others)

1. `annas.py search "<title> <author>" --ext pdf` (or epub) → pick one edition → `annas.py fetch <md5> --ingest --run R` (metadata only).
2. `annas.py download <md5>` → `document.py fetch data/books/<md5>.<ext> --ingest --run R` (real text, chunked). A DDoS-Guard page means CHECKPOINT: `agent_browser.py vnc`, ask the user to solve it, retry once; otherwise report and queue.
3. Mine in order, 8000-char chunks, all chunks or skip with a reason (`content done --upto-seq`). A book without full text yields **no cards**.
4. Link the book to its author (`person`), and to the people it names as mentors (queue, `origin=citation`).

## 4. Papers

`papers.py search|trending` (arXiv), `research.py search --filter` (OpenAlex/Semantic Scholar/SSRN-style), then `fetch <id> [--pdf]` to get the **full text**; abstract-only is allowed only for triage and marks cards `evidence_level: claimed` with a note. Link authors to persons with `research.py profile` (OpenAlex id in `external_ids`). Papers with code: `github.py` for the repository, read its README and results, do not run foreign code.

## 5. Executives, central bankers, regulators

Primary sources: speeches, testimony, letters, interviews, annual letters (`web.py fetch` on the institution's own site, `sec.py` for filings, `youtube.py` for official channels). Profile fields from the institution's official bio page. Cards only from the text of what they said.

## 6. One video or short from someone you do not know

`youtube.py fetch <url> --ingest` → read the description and channel (`youtube.py profile <channel url> --ingest`) → who speaks? (`person-matcher`, guests named in the title/description) → if in scope, `person-explorer` on the channel or the person's own site; if the speaker is a guest, search for their own channel/site and homepage.

## 7. "Find 20–30 new people on X"

Search with `web_search.py` / `youtube.py search --type channel` / `podcast.py search` / `substack.py search`, collect candidates, drop duplicates with `person candidates`, apply the gate, and run the per-person loop on each. Report the names that passed, the ones skipped and why.

## 8. Reporting

End every task with: audit before/after, counts (listed / fetched / mined / cards), blocked (platform, code, hint), queued, doubts. Never report a number you did not read from a command.

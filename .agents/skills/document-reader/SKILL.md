---
name: document-reader
description: Read local or downloaded documents — PDF books and papers (with OCR for scanned pages), EPUB, DOCX, HTML, Markdown and text, including chat exports from Zalo/WhatsApp/Telegram saved as text, and audio/video recordings (webinars, course videos) transcribed with Whisper — into page-, paragraph- or time-level segments stored as FinSocNet content; also scans the user's drop folder data/inbox/documents/. Use for files the user provides, books from Anna's Archive, PDFs from papers or web pages, "read this PDF/book".
license: MIT
compatibility: FinSocNet repository with PyMuPDF, ebooklib, python-docx; audio-transcriber for recordings; optional ocr extra (ocrmypdf + tesseract).
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Document Reader

Every page or paragraph becomes a quotable segment. Big books are fine; the miner reads them in 8000-char chunks.

## When to use

- A local path, a downloaded PDF/EPUB, the drop folder, document URLs.

## Before you start

- For OCR: `uv sync --extra ocr` and tesseract installed.

## Commands

```bash
S=.agents/skills/document-reader/scripts/document.py
uv run $S fetch <path-or-url> [--title T] [--author A] [--source-id S] [--ocr auto|force|off] [--ingest]
uv run $S scan [--dir data/inbox/documents] [--ingest]
```

| Command | Returns |
|---|---|
| `fetch <path-or-url>` | ContentRecord |
| `scan` | ingest every new file; processed files move to `done/` |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

Implements only `fetch` of the adapter contract; other subcommands exit 2 `UNSUPPORTED`.

## Procedure

1. `uv run finsocnet kb run start --skill document-reader --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. User dropped files: `scan --ingest --run R` → for each content: person-matcher (author) → market-idea-miner.
3. Book from Anna's Archive: `fetch data/books/<md5>.<ext> --ingest --run R` (id becomes `book:<md5>`).
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `book:<md5>` (Anna's Archive), `arxiv:<id>`, else `file:<sha256[:16]>` |
| content_type | `book` (> 80 pages or EPUB), `paper`, `recording`, `file` |
| segments | PDF `page {page}`; EPUB `paragraph {chapter, para}`; DOCX/HTML/MD/TXT `paragraph {para}`; audio/video `transcript {start_sec, end_sec}` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill document-reader --kind script_bug …` with the error, then report |

## Notes

- Pages with < 50 chars of text trigger OCR when `--ocr auto`.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.

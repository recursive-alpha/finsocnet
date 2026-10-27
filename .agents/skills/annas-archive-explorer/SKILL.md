---
name: annas-archive-explorer
description: Explore Anna's Archive (https://annas-archive.gl) to discover and retrieve trading books, technical analysis textbooks, quant research papers, and download mirrors by title, author, or MD5 hash.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Anna's Archive Explorer

Research tool for Anna's Archive (`https://annas-archive.gl`) to find trading books, academic finance papers, author bibliographies, and download mirrors across LibGen, Z-Library, and Sci-Hub.

## Capabilities
1. **Search Catalog:** Search by title, author, topic, or ISBN with format filters (`--ext pdf`, `--ext epub`).
2. **Book Details & Mirrors:** Extract descriptions and direct download mirrors for any MD5 hash.
3. **Session & DDoS-Guard Manager:** Interactive browser session saver to `data/sessions/annas_archive_session.json`.
4. **Knowledge DB Integration:** Ingests discovered books and texts directly into `data/knowledge.db` (`platform='annas_archive'`).

## Usage

### 1. Search for Trading Books
```bash
uv run .agents/skills/annas-archive-explorer/scripts/search_archive.py "Market Wizards" --ext pdf --ingest-db
```

### 2. Inspect Specific Book by MD5 or URL
```bash
uv run .agents/skills/annas-archive-explorer/scripts/get_book_details.py "86288c0a3bf9f6f84c12558338407e76"
```

### 3. Clear DDoS-Guard Session (Interactive)
```bash
uv run .agents/skills/annas-archive-explorer/scripts/session_manager.py --interactive
```

## References
See [references/annas_archive_guide.md](references/annas_archive_guide.md) for mirror domains and search operator guidelines.

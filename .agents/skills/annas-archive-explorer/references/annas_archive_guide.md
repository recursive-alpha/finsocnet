# Anna's Archive Exploration Guide

## Overview
Anna's Archive (`https://annas-archive.gl`) aggregates millions of open books, papers, and textbooks from Library Genesis (LibGen), Sci-Hub, Z-Library, and Internet Archive.

## Search Capabilities
- Title / Author / Topic keyword search.
- Filter by file format: `--ext pdf`, `--ext epub`, `--ext mobi`.
- Filter by language: `--lang en`.
- Direct MD5 lookup for verified book editions.

## Handling DDoS-Guard Challenge
`annas-archive.gl` uses DDoS-Guard protection on direct requests.
- **Method 1 (Saved Session):** Run `session_manager.py --interactive` once. Pass the check in the visible browser window, and the cookies will be stored in `data/sessions/annas_archive_session.json` for subsequent headless searches.
- **Method 2 (Search Index Fallback):** `annas.py search` reports a DDoS-Guard checkpoint (exit 3) instead of silently falling back to search index queries (`site:annas-archive.gl`) to discover exact book titles and MD5 hashes when unauthenticated.

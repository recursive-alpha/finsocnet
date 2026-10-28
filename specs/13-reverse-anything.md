# 13 — Reverse Anything (REA bridge)

Code: `finsocnet/adapters/rea.py`, skill `reverse-anything` (`scripts/rea.py`). Upstream: https://github.com/morluto/rea (MIT). Purpose: make content the agent cannot read — binaries, packaged apps, databases, captures, model files — readable and searchable.

## 1. Scope

REA turns an artifact into **Evidence**: observations with provenance, `confidence` (`observed` > `derived` > `hypothesis`), `authority`, `coverage` and `limitations`. The bridge runs REA's **static, read-only** inspections and stores the Evidence as a `file` content:

- `kinds`: `auto` (REA `inspect-artifact`), `entropy`, `layout`, `sqlite`, `model`, `pcap`, `js-app`, `apk`, `go`, `rust`, `pe-imports`, `pe-resources`, `elf-notes`, `macho`, `pyc`, `plist`, `ips`, `kernel-module`, `il2cpp`, `beam`, `firmware`, `desktop-app`; `--kind detect` picks one from name and magic bytes.
- Not exposed: function-level decompilation (needs Hopper/Ghidra/IDA), process/browser/Electron scenario capture, adb, debuggers, firmware extraction, environment building. They run the target or talk to devices; use REA's MCP tools with the user's consent.

## 2. Safety (normative)

1. **Static only**: a unit test fails if a command name contains `capture-`, `debug`, `adb`, `install`, `frida`, … or does not start with `inspect-` / `analyze-`.
2. **Output is untrusted data.** Records carry `extra.untrusted_content = true`; the skill tells the agent to report instruction-like strings found in artifacts instead of obeying them.
3. **No shell, no stdin, scratch working directory, minimal environment** (`PATH`, `HOME`, `LANG`, `TMPDIR`, `REA_*`); the path is one argv element.
4. **No self-installation.** If `rea` is not on `PATH` the command exits `UNSUPPORTED` with the install hint. `FINSOCNET_ALLOW_NPX=1` (the user's choice) permits `npx -y rea-agents@<pinned>`; the version is pinned (`FINSOCNET_REA_VERSION`, default 6.8.0, the tested release).
5. The original file is never modified or moved.

## 3. Record

`id = file:<sha256(file sha | command)[:16]>` (idempotent per file and command), `platform file`, `content_type file`, English, `fetch_method rea:<command>`, source `file:site:rea-artifacts`. Segments: `summary` (name, format, SHA-256, operation, confidence, authority, evidence id), one group per section of `normalized_result` split to ≤ 3500 chars (`code` segments, locator `{section, part}`), and `limitations`. At most 400 segments; the full Evidence is kept in `data/raw/rea/` (`raw_path`).

## 4. Commands

`rea.py doctor` · `rea.py kinds` · `rea.py fetch <path> [--kind K] [--extra=ARG]… [--full] [--ingest --run R]` (standard platform flags; exit codes per 00: 2 not installed, 5 missing path, 6 REA refused, 4 timeout `FINSOCNET_REA_TIMEOUT`, 1 REA printed no JSON).

## 5. Acceptance

Tests with a stub `rea`: kind detection, Evidence→record validity and chunking, same file+command → same id, no-shell invocation with hostile file names, failure mapping, static-only command set. Live check: `inspect-artifact /bin/ls` and `inspect-sqlite-database` on a copy of the knowledge base.

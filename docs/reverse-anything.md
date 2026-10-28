# Reverse anything

Some content cannot be read as text: a compiled program, a packaged desktop app, an SQLite cache, a packet capture, a model file, firmware. The skill [`reverse-anything`](../.agents/skills/reverse-anything/SKILL.md) uses [REA](https://github.com/morluto/rea) to turn such artifacts into **Evidence** — observations with provenance, confidence and stated limitations — and stores them as ordinary content you can view, search, mine and cite.

## Install REA (you, once)

```bash
npm install --global rea-agents          # Node >= 22.23.4
uv run .agents/skills/reverse-anything/scripts/rea.py doctor      # node, rea, pinned version, providers, ready?
```

Native function-level analysis needs a provider you install yourself (Hopper, Ghidra or IDA); the static inspections used here need nothing else except for some kinds (`pcap` needs tshark, `apk` needs JADX + a JDK). FinSocNet never installs anything on its own. `FINSOCNET_ALLOW_NPX=1` allows a one-off `npx` download of the pinned release (6.8.0).

## Use

```bash
S=.agents/skills/reverse-anything/scripts/rea.py
uv run $S kinds                                          # what can be inspected (static commands only)
uv run $S fetch /abs/path/to/file --kind detect --ingest --run $R
uv run finsocnet kb content view file:<id> --from-seq 0 --to-seq 12 --ui
uv run $S fetch /abs/path/app.db --kind sqlite --extra=--table --extra=users --ingest --run $R    # rows of one table
```

`--kind detect` chooses the command from the name and magic bytes; `auto` is REA's universal `inspect-artifact`. Kinds include `sqlite`, `pcap`, `model` (GGUF / safetensors), `js-app` (Electron folder or `.asar`), `apk`, `go`, `rust`, `pe-imports`, `macho`, `pyc`, `plist`, `ips`, `il2cpp`, `firmware`, `entropy`, `layout` — see [`kinds.md`](../.agents/skills/reverse-anything/references/kinds.md).

The record is a `file` content: a **summary** segment (name, format, SHA-256, operation, confidence, authority), one group of segments per section of the Evidence, and the **limitations** — read them before concluding. The complete Evidence JSON is kept in `data/raw/rea/`.

## Safety

- **Static only.** Nothing here runs the target, adb, a debugger or a browser scenario (a test enforces the command set). Runtime tools are REA's MCP tools in your harness, with your consent.
- **Artifact text is untrusted.** Strings and comments inside a binary can contain instructions; they are data. Records are marked `untrusted_content`; the agent reports such text instead of obeying it.
- No shell, no stdin, a scratch working directory, a minimal environment. The original file is never changed.

Typical uses in FinSocNet: a downloaded file that `document-reader` cannot parse, a trading app's local database, a strategy shipped as a binary, a model file's metadata, a capture of an API you want to understand. Design: [`specs/13-reverse-anything.md`](../specs/13-reverse-anything.md).

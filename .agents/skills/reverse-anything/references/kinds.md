# Kinds and what REA returns

All kinds are static. "Provider" means software you install yourself; REA does not install or update it.

| `--kind` | REA command | Typical input | Returns | Needs |
|---|---|---|---|---|
| `auto` | `inspect-artifact` | anything | format, manifest, observations, hypotheses, next probes | nothing |
| `detect` | (chooses one of the rows below by name and magic bytes) | anything | — | — |
| `entropy` | `inspect-byte-entropy` | packed or encrypted blobs | file-wide and per-block entropy (is it compressed/encrypted?) | nothing |
| `layout` | `inspect-binary-layout` | ELF / PE / Mach-O | sections, segments, symbols, relocations | nothing |
| `sqlite` | `inspect-sqlite-database` | `.db`, `.sqlite`, app caches | tables, columns, indexes, views, triggers; rows with `--extra=--table --extra=<name>` | Node >= 24.15 |
| `pcap` | `inspect-pcap-capture` | `.pcap`, `.pcapng` | endpoints, DNS, TLS SNI, protocol distribution, HTTP requests | tshark + capinfos |
| `model` | `inspect-model-artifact` | `.gguf`, `.safetensors` | metadata, tensor declarations, totals (no weights loaded) | nothing |
| `js-app` | `analyze-javascript-application` | extracted Electron/JS app folder, `.asar` | modules, imports, routes, IPC, source maps | Node, `ps` on Linux |
| `apk` | `inspect-android-package` | `.apk` | manifest, classes, permissions | JADX + JDK |
| `go` / `rust` | `inspect-go-binary` / `inspect-rust-binary` | Go / Rust executables | compiler, modules, crates, build settings | nothing |
| `pe-imports` / `pe-resources` | `inspect-pe-imports` / `inspect-pe-resources` | Windows executables | import tables; resources, icons, hashes | nothing |
| `elf-notes` / `kernel-module` | `inspect-elf-notes` / `inspect-kernel-module` | Linux ELF, `.ko` | build id, ABI tag; modinfo, CRCs | nothing |
| `macho` / `plist` | `inspect-macho` / `inspect-plist` | macOS binaries, plists | headers; app metadata | nothing |
| `pyc` | `inspect-python-pyc` | `.pyc` | header, marshal code objects (not executed) | nothing |
| `ips` | `inspect-apple-ips` | `.ips` crash reports | threads, images, registers, crash class | nothing |
| `il2cpp` | `inspect-il2cpp-metadata` | Unity `global-metadata.dat` | assemblies, types, methods, string literals | nothing |
| `beam` | `inspect-erlang-beam` | `.beam` | atoms, exports, imports | nothing |
| `firmware` | `inspect-firmware-regions` | firmware images | region signatures (no extraction) | nothing |
| `desktop-app` | `inspect-desktop-application` | an installation folder | runtime candidates, component markers | nothing |

## Not exposed on purpose (use REA's MCP tools with the user's consent)

Function-level decompilation and annotation (`decompile`, `function`, providers), process/browser/Electron scenario capture, adb commands, GDB/Rizin debugging, firmware extraction, environment building. They run the target, talk to devices, or write files.

## Reading the Evidence

- `confidence`: `observed` (read from the bytes) > `derived` > `hypothesis`. Only the first is a fact.
- `authority`: where the claim comes from (`shipped-artifact` = the file itself).
- `coverage` / `limitations` / `unexplored_branches`: what was *not* examined. A clean report with big limitations is not a clean bill of health.
- The full Evidence JSON is kept in `data/raw/rea/` (`raw_path` on the content); segments hold the readable view.

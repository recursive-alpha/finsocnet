"""REA bridge: turn files an agent cannot read (binaries, packaged apps, databases, captures, model files) into text Evidence
(https://github.com/morluto/rea, specs/13-reverse-anything.md).

Only REA's *static* inspection commands are exposed here: nothing in this module runs the target, adb, a debugger or a browser scenario.
REA's output is data about an untrusted artifact (strings, symbols and file contents can contain instructions): it is stored as content and
never interpreted as instructions by anything in this repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from finsocnet.core import config
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, save_raw

REA_VERSION = os.getenv("FINSOCNET_REA_VERSION", "6.8.0")  # pinned: the version this adapter was tested with
TIMEOUT_S = int(os.getenv("FINSOCNET_REA_TIMEOUT", "300"))
SEGMENT_CHARS = 3500
MAX_SEGMENTS = 400

# kind -> REA CLI command. Static, read-only inspections only (REA docs: "without executing the image / target").
COMMANDS: dict[str, str] = {
    "auto": "inspect-artifact",            # universal: format, manifest, observations, next probes
    "entropy": "inspect-byte-entropy",
    "layout": "inspect-binary-layout",
    "sqlite": "inspect-sqlite-database",
    "model": "inspect-model-artifact",     # GGUF / safetensors headers
    "pcap": "inspect-pcap-capture",
    "js-app": "analyze-javascript-application",   # extracted Electron/JS app directory or .asar
    "apk": "inspect-android-package",
    "go": "inspect-go-binary",
    "rust": "inspect-rust-binary",
    "pe-imports": "inspect-pe-imports",
    "pe-resources": "inspect-pe-resources",
    "elf-notes": "inspect-elf-notes",
    "macho": "inspect-macho",
    "pyc": "inspect-python-pyc",
    "plist": "inspect-plist",
    "ips": "inspect-apple-ips",
    "kernel-module": "inspect-kernel-module",
    "il2cpp": "inspect-il2cpp-metadata",
    "beam": "inspect-erlang-beam",
    "firmware": "inspect-firmware-regions",
    "desktop-app": "inspect-desktop-application",
}
KINDS = tuple(COMMANDS)


def detect_kind(path: Path) -> str:
    """Pick the most specific static command for `path` from its name and first bytes (REA's inspect-artifact is the fallback)."""
    if path.is_dir():
        return "js-app" if (path / "package.json").exists() or (path / "resources").exists() or any(path.glob("*.asar")) else "desktop-app"
    name = path.name.lower()
    try:
        head = path.open("rb").read(64)
    except OSError:
        head = b""
    if name.endswith(".asar"):
        return "js-app"
    if head.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if head[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x0a\x0d\x0d\x0a", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d"):
        return "pcap"
    if head.startswith(b"GGUF") or name.endswith((".safetensors", ".gguf")):
        return "model"
    if name.endswith((".apk", ".aab")):
        return "apk"
    if name.endswith(".pyc"):
        return "pyc"
    if name.endswith(".ips"):
        return "ips"
    if name.endswith(".plist") or head.startswith(b"bplist00"):
        return "plist"
    if name.endswith(".ko"):
        return "kernel-module"
    if name.endswith(".beam"):
        return "beam"
    return "auto"


def rea_command() -> list[str]:
    """The `rea` executable if installed, else `npx` pinned to REA_VERSION when the user allowed it (FINSOCNET_ALLOW_NPX=1)."""
    exe = shutil.which("rea")
    if exe:
        return [exe]
    if os.getenv("FINSOCNET_ALLOW_NPX") == "1" and shutil.which("npx"):
        return [shutil.which("npx") or "npx", "-y", f"rea-agents@{REA_VERSION}"]
    raise CliError("UNSUPPORTED", "REA is not installed",
                   "Install it yourself (`npm install --global rea-agents`, Node >= 22.23.4), or allow a one-off download of the pinned version with FINSOCNET_ALLOW_NPX=1. "
                   "See https://github.com/morluto/rea")


def doctor() -> dict[str, Any]:
    node = shutil.which("node")
    out: dict[str, Any] = {"node": None, "rea": shutil.which("rea"), "npx": shutil.which("npx"), "pinned_version": REA_VERSION,
                           "npx_allowed": os.getenv("FINSOCNET_ALLOW_NPX") == "1", "providers": {k: os.getenv(k) for k in ("REA_PROVIDER", "REA_GHIDRA_PATH", "REA_HOPPER_PATH") if os.getenv(k)}}
    if node:
        out["node"] = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
    try:
        out["command"] = rea_command()
        out["ready"] = True
    except CliError as e:
        out["ready"] = False
        out["problem"] = e.message
        out["hint"] = e.hint
    return out


def run_rea(args: list[str], timeout: int = TIMEOUT_S) -> Any:
    """Run one REA CLI command (argument list, no shell, no stdin, scratch working directory) and parse its JSON."""
    cmd = [*rea_command(), *args, "--json"]
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "TMPDIR") or k.startswith("REA_")}
    with tempfile.TemporaryDirectory(prefix="finsocnet-rea-") as tmp:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmp, env=env, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired as e:
            raise CliError("RATE_LIMITED", f"REA did not finish in {timeout}s", "raise FINSOCNET_REA_TIMEOUT or pick a narrower command (--kind)", retry_after_sec=0) from e
    text = p.stdout.strip()
    try:
        data = json.loads(text)
    except ValueError:
        raise CliError("INTERNAL", f"REA exit {p.returncode} without JSON: {(p.stderr or text)[:300]}", "run `rea doctor` and check the provider setup for this file type") from None
    if p.returncode != 0 or (isinstance(data, dict) and data.get("ok") is False):
        err = data.get("error") if isinstance(data, dict) else None
        msg = (err or {}).get("message") if isinstance(err, dict) else str(err or data)[:300]
        raise CliError("VALIDATION_ERROR", f"REA refused: {str(msg)[:300]}", "see `rea capabilities`; some file types need a provider (Hopper, Ghidra, IDA) that you set up yourself")
    return data


def _chunks(label: str, value: Any, limit: int = SEGMENT_CHARS) -> list[tuple[str, str]]:
    """Split one Evidence section into readable text pieces of at most `limit` characters."""
    if isinstance(value, list) and len(value) > 1:
        out: list[tuple[str, str]] = []
        buf: list[str] = []
        size = 0
        for item in value:
            line = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if size + len(line) > limit and buf:
                out.append((label, "\n".join(buf)))
                buf, size = [], 0
            if len(line) > limit:  # one huge item: cut it, the raw Evidence file has the rest
                line = line[:limit - 20] + " …(truncated)"
            buf.append(line)
            size += len(line) + 1
        if buf:
            out.append((label, "\n".join(buf)))
        return out
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True)
    return [(label, text[i:i + limit]) for i in range(0, max(len(text), 1), limit)] if text.strip() else []


def evidence_to_record(ev: dict[str, Any], src: Path, kind: str, command: str, file_sha: str, raw_path: str | None) -> dict[str, Any]:
    """A ContentRecord from an Evidence envelope: a summary, one group of segments per section of `normalized_result`, and the limitations."""
    subj = ev.get("subject") or {}
    norm = ev.get("normalized_result")
    fmt = subj.get("format") or kind
    summary = "\n".join(l for l in (
        f"File: {src.name}", f"Format: {fmt}", f"Architecture: {subj.get('architecture')}" if subj.get("architecture") else "",
        f"SHA-256: {file_sha}", f"REA operation: {ev.get('operation') or command} (provider {((ev.get('provider') or {}).get('name')) or 'rea'})",
        f"Confidence: {ev.get('confidence')}; authority: {ev.get('authority')}", f"Evidence id: {ev.get('evidence_id')}") if l)
    segs: list[dict[str, Any]] = [{"seq": 0, "kind": "paragraph", "locator": {"section": "summary"}, "text": summary}]
    sections = norm.items() if isinstance(norm, dict) else [("result", norm)]
    for key, val in sections:
        if val in (None, [], {}, ""):
            continue
        for part, (label, text) in enumerate(_chunks(key, val)):
            segs.append({"seq": 0, "kind": "code", "locator": {"section": label, "part": part}, "text": f"[{label}]\n{text}"})
            if len(segs) >= MAX_SEGMENTS:
                break
        if len(segs) >= MAX_SEGMENTS:
            segs.append({"seq": 0, "kind": "paragraph", "locator": {"section": "truncated"}, "text": f"Output truncated at {MAX_SEGMENTS} segments; the full Evidence is in {raw_path}."})
            break
    lim = ev.get("limitations") or (norm or {}).get("limitations") if isinstance(norm, dict) else ev.get("limitations")
    if lim:
        segs.append({"seq": 0, "kind": "paragraph", "locator": {"section": "limitations"}, "text": "Limitations reported by REA:\n" + "\n".join(f"- {l}" for l in (lim if isinstance(lim, list) else [str(lim)]))})
    cid = "file:" + hashlib.sha256(f"{file_sha}|{command}".encode()).hexdigest()[:16]
    return content_record(cid, "file", "file", segs, title=f"{src.name} ({fmt}, REA {command})", description=summary.splitlines()[1] if summary else None,
                          fetch_method=f"rea:{command}", raw_path=raw_path, language="en",
                          extra={"rea": {"operation": ev.get("operation"), "evidence_id": ev.get("evidence_id"), "command": command, "kind": kind, "rea_version": REA_VERSION},
                                 "sha256": file_sha, "path_name": src.name, "untrusted_content": True},
                          source={"id": "file:site:rea-artifacts", "kind": "site", "title": "Artifacts inspected with REA"})


def sha256_path(p: Path) -> str:
    if p.is_file():
        h = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    h = hashlib.sha256()  # a directory: hash the relative file list with sizes (cheap, stable)
    for q in sorted(x for x in p.rglob("*") if x.is_file())[:5000]:
        h.update(f"{q.relative_to(p)}|{q.stat().st_size}\n".encode())
    return h.hexdigest()


class Rea(PlatformAdapter):
    platform = "file"
    capabilities = frozenset({"fetch"})
    opts = {"fetch": [(("--kind",), {"default": "auto", "choices": ["detect", *KINDS], "help": "REA static command to use; detect = by name and magic bytes, auto = REA's inspect-artifact"}),
                      (("--extra",), {"action": "append", "default": [], "help": "extra REA argument (repeatable), e.g. --extra=--table --extra=users"})]}

    def fetch(self, item, *, kind="auto", extra=None, **_):
        p = Path(item).expanduser()
        if "\x00" in item or not p.exists():
            raise CliError("NOT_FOUND", f"{item!r} does not exist", "give an absolute path to the file or directory")
        p = p.resolve()
        if kind == "detect":
            kind = detect_kind(p)
        command = COMMANDS[kind]
        ev = run_rea([command, str(p), *(extra or [])])
        if not isinstance(ev, dict):
            raise CliError("INTERNAL", "REA returned an unexpected JSON shape")
        sha = sha256_path(p)
        rec_id = "rea-" + hashlib.sha256(f"{sha}|{command}".encode()).hexdigest()[:16]
        raw = save_raw("rea", rec_id, ev)
        return evidence_to_record(ev, p, kind, command, sha, raw)

"""REA bridge (specs/13-reverse-anything.md): kind detection, Evidence -> ContentRecord, static-only command set, failure mapping. A stub `rea` stands in for the CLI."""

from __future__ import annotations

import json
import stat

import pytest

from finsocnet.adapters import rea
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors

EVIDENCE = {"evidence_id": "ev_abc", "subject": {"name": "app", "format": "elf", "architecture": "x86_64"}, "provider": {"name": "REA safe artifact graph provider"},
            "operation": "inspect_artifact", "confidence": "observed", "authority": "shipped-artifact", "limitations": ["static only", "no execution"],
            "normalized_result": {"inspection_id": "ai_1", "observations": [{"kind": "string", "value": f"s{i}" * 40} for i in range(120)], "next_probes": [{"operation": "open_binary"}], "empty": []}}


@pytest.fixture
def stub(tmp_path, monkeypatch):
    def make(stdout: str, code: int = 0):
        exe = tmp_path / "bin" / "rea"
        exe.parent.mkdir(exist_ok=True)
        exe.write_text(f"#!/bin/sh\necho \"$@\" > {tmp_path}/argv.txt\ncat <<'EOF'\n{stdout}\nEOF\nexit {code}\n")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{exe.parent}:/usr/bin:/bin")
        return tmp_path / "argv.txt"
    return make


def test_detect_kind(tmp_path):
    (tmp_path / "a.db").write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    (tmp_path / "m.gguf").write_bytes(b"GGUF" + b"\x00" * 10)
    (tmp_path / "c.pcap").write_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
    (tmp_path / "x.apk").write_bytes(b"PK\x03\x04")
    (tmp_path / "prog").write_bytes(b"\x7fELF" + b"\x00" * 20)
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "package.json").write_text("{}")
    got = {n: rea.detect_kind(tmp_path / n) for n in ("a.db", "m.gguf", "c.pcap", "x.apk", "prog", "app")}
    assert got == {"a.db": "sqlite", "m.gguf": "model", "c.pcap": "pcap", "x.apk": "apk", "prog": "auto", "app": "js-app"}


def test_only_static_commands_are_exposed():
    banned = ("capture-", "debug", "adb", "install", "uninstall", "push", "pull", "frida", "start-", "stop-", "instrument", "observe", "load-frida")
    assert all(not any(b in c for b in banned) for c in rea.COMMANDS.values()), rea.COMMANDS
    assert all(c.startswith(("inspect-", "analyze-")) for c in rea.COMMANDS.values())


def test_evidence_becomes_a_valid_chunked_record(tmp_path):
    f = tmp_path / "app"
    f.write_bytes(b"\x7fELF")
    rec = rea.evidence_to_record(EVIDENCE, f, "auto", "inspect-artifact", "ab" * 32, "data/raw/rea/x.json")
    assert schema_errors("content_record", rec) == []
    assert rec["id"].startswith("file:") and rec["platform"] == "file" and rec["extra"]["untrusted_content"] is True
    texts = [s["text"] for s in rec["segments"]]
    assert texts[0].startswith("File: app") and "Format: elf" in texts[0] and all(len(t) <= rea.SEGMENT_CHARS + 40 for t in texts)
    assert sum(1 for s in rec["segments"] if s["locator"].get("section") == "observations") >= 2  # the 120 observations were split
    assert not any(s["locator"].get("section") == "empty" for s in rec["segments"])
    assert "static only" in texts[-1] and rec["segments"][-1]["locator"]["section"] == "limitations"
    again = rea.evidence_to_record(EVIDENCE, f, "auto", "inspect-artifact", "ab" * 32, None)
    other = rea.evidence_to_record(EVIDENCE, f, "auto", "inspect-byte-entropy", "ab" * 32, None)
    assert again["id"] == rec["id"] != other["id"]  # same file + same command -> same id (idempotent); another command -> another report


def test_fetch_runs_the_command_without_a_shell(tmp_path, stub):
    argv = stub(json.dumps(EVIDENCE))
    target = tmp_path / "weird name; rm -rf $HOME"
    target.write_bytes(b"\x7fELF" + b"\x00" * 32)
    rec = rea.Rea().fetch(str(target), kind="entropy")
    assert rec["fetch_method"] == "rea:inspect-byte-entropy"
    assert argv.read_text().split()[0] == "inspect-byte-entropy" and argv.read_text().strip().endswith("--json")
    assert str(target) in argv.read_text()


def test_failures_map_to_the_envelope(tmp_path, stub, monkeypatch):
    target = tmp_path / "x.bin"
    target.write_bytes(b"1234")
    stub("not json at all")
    with pytest.raises(CliError) as e:
        rea.Rea().fetch(str(target))
    assert e.value.code == "INTERNAL"
    stub(json.dumps({"ok": False, "error": {"message": "provider not configured"}}), code=2)
    with pytest.raises(CliError) as e:
        rea.Rea().fetch(str(target))
    assert e.value.code == "VALIDATION_ERROR" and "provider not configured" in e.value.message
    with pytest.raises(CliError) as e:
        rea.Rea().fetch(str(tmp_path / "missing"))
    assert e.value.code == "NOT_FOUND"
    monkeypatch.setenv("PATH", "/nonexistent")
    monkeypatch.delenv("FINSOCNET_ALLOW_NPX", raising=False)
    with pytest.raises(CliError) as e:
        rea.rea_command()
    assert e.value.code == "UNSUPPORTED" and "FINSOCNET_ALLOW_NPX" in e.value.hint

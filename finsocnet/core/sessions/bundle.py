"""Encrypted session bundles (specs/04 §3.2): age-encrypted tar.gz of manifest, cookies, localStorage, history."""

from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyrage
from pyrage import x25519

from finsocnet.core import ids
from finsocnet.core.sessions import formats

DEFAULT_IDENTITY = "~/.config/finsocnet/age_identity.txt"


def generate_identity(path: Path) -> str:
    """Create an age identity at `path` (chmod 600, parent chmod 700) and return its public recipient."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    ident = x25519.Identity.generate()
    path.write_text(str(ident) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return str(ident.to_public())


def load_identity(path: Path) -> x25519.Identity:
    return x25519.Identity.from_str(path.expanduser().read_text(encoding="utf-8").strip().splitlines()[-1])


def recipient_of(identity_path: Path) -> str:
    return str(load_identity(identity_path).to_public())


def _add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    tar.addfile(info, io.BytesIO(data))


def build_bundle(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]], history: list[dict[str, Any]],
                 recipient: str, source: dict[str, Any], excluded: list[str] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Return (encrypted bytes, manifest). The plaintext only ever exists in memory."""
    manifest = {
        "bundle_id": ids.bundle_id(), "created_at": ids.utc_now(), "source": source,
        "domains": formats.domain_summary(cookies, local_storage), "excluded_domains": excluded or [],
        "counts": {"cookies": len(cookies), "domains": len(formats.domain_summary(cookies, local_storage)),
                   "local_storage_origins": len(local_storage), "history_entries": len(history)},
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        _add(tar, "manifest.json", json.dumps(manifest).encode())
        _add(tar, "cookies.json", json.dumps(cookies).encode())
        _add(tar, "local_storage.json", json.dumps(local_storage).encode())
        if history:
            _add(tar, "history.jsonl", "\n".join(json.dumps(h) for h in history).encode())
    return pyrage.encrypt(buf.getvalue(), [x25519.Recipient.from_str(recipient)]), manifest


def read_bundle(data: bytes, identity_path: Path) -> dict[str, Any]:
    plain = pyrage.decrypt(data, [load_identity(identity_path)])
    out: dict[str, Any] = {"history": []}
    with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile() or "/" in m.name or m.name.startswith("."):
                continue  # flat archive only; never extract to disk
            raw = tar.extractfile(m).read()  # type: ignore[union-attr]
            if m.name == "manifest.json":
                out["manifest"] = json.loads(raw)
            elif m.name == "cookies.json":
                out["cookies"] = [formats.norm_cookie(c) for c in json.loads(raw)]
            elif m.name == "local_storage.json":
                out["local_storage"] = json.loads(raw)
            elif m.name == "history.jsonl":
                out["history"] = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    out.setdefault("cookies", [])
    out.setdefault("local_storage", {})
    return out

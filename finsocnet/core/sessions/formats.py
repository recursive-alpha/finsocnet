"""Readers and writers for every cookie/session input format (docs/spec/04 §3.1). Normalized cookie:
`{name, value, domain, path, expires (epoch seconds, -1 = session), httpOnly, secure, sameSite (Strict|Lax|None|null), partitionKey?}`."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COOKIE_KEYS = ("name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite")
TWO_LEVEL = {"co.uk", "org.uk", "ac.uk", "com.au", "net.au", "co.jp", "com.vn", "net.vn", "org.vn", "com.br", "co.nz", "com.sg", "co.in", "com.hk", "com.cn"}
SAMESITE = {"strict": "Strict", "lax": "Lax", "none": "None", "no_restriction": "None", "unspecified": None, "": None, None: None}
FIREFOX_SAMESITE = {0: "None", 1: "Lax", 2: "Strict"}
WEBKIT_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and 1970-01-01


def norm_cookie(c: dict[str, Any]) -> dict[str, Any]:
    exp = c.get("expires", c.get("expirationDate", -1))
    try:
        exp = float(exp)
    except (TypeError, ValueError):
        exp = -1.0
    if exp <= 0:
        exp = -1.0
    ss = c.get("sameSite")
    ss = SAMESITE.get(str(ss).lower() if ss is not None else None, ss if ss in ("Strict", "Lax", "None") else None)
    out = {"name": str(c["name"]), "value": str(c.get("value", "")), "domain": str(c.get("domain") or c.get("host") or ""),
           "path": str(c.get("path") or "/"), "expires": exp, "httpOnly": bool(c.get("httpOnly", c.get("httponly", False))),
           "secure": bool(c.get("secure", False)), "sameSite": ss}
    if c.get("partitionKey"):
        out["partitionKey"] = c["partitionKey"]
    return out


def registrable_domain(domain: str) -> str:
    d = domain.lstrip(".").lower()
    parts = d.split(".")
    if len(parts) <= 2:
        return d
    if ".".join(parts[-2:]) in TWO_LEVEL and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def cookie_key(c: dict[str, Any]) -> tuple[str, str, str]:
    return (c["name"], c["domain"].lstrip(".").lower(), c["path"])


def merge_cookies(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same (name, domain, path): the newest `expires` wins (session cookies, -1, lose against dated ones)."""
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for c in cookies:
        k = cookie_key(c)
        if k not in best or c["expires"] > best[k]["expires"]:
            best[k] = c
    return list(best.values())


def drop_expired(cookies: list[dict[str, Any]], now: float | None = None) -> tuple[list[dict[str, Any]], int]:
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    keep = [c for c in cookies if c["expires"] == -1 or c["expires"] > now]
    return keep, len(cookies) - len(keep)


# --- parsers --------------------------------------------------------------------------------------------

def parse_netscape(text: str) -> list[dict[str, Any]]:
    out = []
    for line in text.splitlines():
        http_only = line.startswith("#HttpOnly_")
        if http_only:
            line = line[len("#HttpOnly_"):]
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) != 7:
            continue
        domain, _sub, path, secure, expires, name, value = f
        out.append(norm_cookie({"name": name, "value": value, "domain": domain, "path": path, "secure": secure.upper() == "TRUE",
                                "expires": expires, "httpOnly": http_only}))
    return out


def parse_cookie_editor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [norm_cookie(c) for c in items if isinstance(c, dict) and "name" in c and ("domain" in c or "host" in c)]


def parse_storage_state(obj: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    cookies = [norm_cookie(c) for c in obj.get("cookies", [])]
    ls: dict[str, dict[str, str]] = {}
    for o in obj.get("origins", []):
        items = {i["name"]: i["value"] for i in o.get("localStorage", []) if "name" in i}
        if items:
            ls[o["origin"]] = items
    return cookies, ls


def parse_har(obj: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for e in obj.get("log", {}).get("entries", []):
        host = ""
        try:
            from urllib.parse import urlsplit
            host = urlsplit(e["request"]["url"]).hostname or ""
        except (KeyError, ValueError):
            pass
        for c in e.get("response", {}).get("cookies", []) + e.get("request", {}).get("cookies", []):
            if "name" in c:
                out.append(norm_cookie({**c, "domain": c.get("domain") or host, "expires": _har_expires(c.get("expires"))}))
    return out


def _har_expires(v: Any) -> float:
    if not v:
        return -1.0
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return -1.0


def _copy_db(path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp()) / path.name
    shutil.copy(path, tmp)
    for ext in ("-wal", "-shm"):
        side = path.with_name(path.name + ext)
        if side.exists():
            shutil.copy(side, tmp.with_name(tmp.name + ext))
    return tmp


def parse_firefox_cookies(path: Path) -> list[dict[str, Any]]:
    tmp = _copy_db(path)
    try:
        conn = sqlite3.connect(tmp)
        rows = conn.execute("SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite FROM moz_cookies").fetchall()
        conn.close()
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return [norm_cookie({"name": n, "value": v, "domain": h, "path": p, "expires": (e / 1000 if e > 1e11 else e), "secure": bool(s),
                         "httpOnly": bool(ho), "sameSite": FIREFOX_SAMESITE.get(ss)}) for n, v, h, p, e, s, ho, ss in rows]


def parse_history(path: Path, kind: str) -> list[dict[str, Any]]:
    """Chrome `History` (urls) or Firefox `places.sqlite` (moz_places); the live file is copied first."""
    tmp = _copy_db(path)
    out: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(tmp)
        if kind == "chrome_history":
            for url, title, visits, last in conn.execute("SELECT url, title, visit_count, last_visit_time FROM urls"):
                ts = (last / 1e6 - WEBKIT_EPOCH_OFFSET) if last else None
                out.append({"url": url, "title": title, "visit_count": visits, "last_visit_at": _iso(ts)})
        else:
            for url, title, visits, last in conn.execute("SELECT url, title, visit_count, last_visit_date FROM moz_places WHERE visit_count > 0"):
                out.append({"url": url, "title": title, "visit_count": visits, "last_visit_at": _iso(last / 1e6 if last else None)})
        conn.close()
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return out


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts and ts > 0 else None


# --- detection ------------------------------------------------------------------------------------------

def detect(path: Path) -> str:
    """Identify a file by content, not by extension."""
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return "unreadable"
    if head.startswith(b"SQLite format 3"):
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError:
            return "unknown"
        finally:
            conn.close()
        if "moz_cookies" in tables:
            return "firefox_cookies"
        if "moz_places" in tables:
            return "firefox_history"
        if "cookies" in tables:
            return "chrome_cookies"
        if "urls" in tables and "visits" in tables:
            return "chrome_history"
        return "unknown"
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return "unknown"
    if text.startswith("# Netscape HTTP Cookie File") or any(len(l.split("\t")) == 7 for l in text.splitlines()[:20] if l and not l.startswith("#")):
        return "netscape"
    try:
        obj = json.loads(text)
    except ValueError:
        return "unknown"
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "name" in obj[0] and ("domain" in obj[0] or "host" in obj[0]):
        return "cookie_editor"
    if isinstance(obj, dict) and ("cookies" in obj or "origins" in obj):
        return "storage_state"
    if isinstance(obj, dict) and "log" in obj and "entries" in obj.get("log", {}):
        return "har"
    return "unknown"


def read_file(path: Path) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, str]], list[dict[str, Any]]]:
    """Return (kind, cookies, local_storage, history) for one file."""
    kind = detect(path)
    cookies: list[dict[str, Any]] = []
    ls: dict[str, dict[str, str]] = {}
    hist: list[dict[str, Any]] = []
    if kind == "netscape":
        cookies = parse_netscape(path.read_text(encoding="utf-8"))
    elif kind == "cookie_editor":
        cookies = parse_cookie_editor(json.loads(path.read_text(encoding="utf-8")))
    elif kind == "storage_state":
        cookies, ls = parse_storage_state(json.loads(path.read_text(encoding="utf-8")))
    elif kind == "har":
        cookies = parse_har(json.loads(path.read_text(encoding="utf-8")))
    elif kind == "firefox_cookies":
        cookies = parse_firefox_cookies(path)
    elif kind in ("firefox_history", "chrome_history"):
        hist = parse_history(path, kind)
    return kind, cookies, ls, hist


def scan_dir(root: Path, include_history: bool = False) -> dict[str, Any]:
    """Detect every file under `root` by content and merge the results; per-file report holds counts only."""
    cookies: list[dict[str, Any]] = []
    ls: dict[str, dict[str, str]] = {}
    hist: list[dict[str, Any]] = []
    files = []
    paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    for p in paths:
        kind, c, l, h = read_file(p)
        if kind == "chrome_cookies":
            files.append({"file": str(p), "kind": kind, "cookies": 0, "note": "Chrome cookies are encrypted; export on the machine that owns them"})
            continue
        if kind in ("unknown", "unreadable"):
            files.append({"file": str(p), "kind": kind, "cookies": 0})
            continue
        if kind.endswith("_history") and not include_history:
            files.append({"file": str(p), "kind": kind, "history_entries": len(h), "note": "skipped without --history"})
            continue
        cookies += c
        for origin, items in l.items():
            ls.setdefault(origin, {}).update(items)
        hist += h
        files.append({"file": str(p), "kind": kind, "cookies": len(c), "local_storage_origins": len(l), "history_entries": len(h)})
    return {"cookies": merge_cookies(cookies), "local_storage": ls, "history": hist, "files": files}


# --- summaries and writers ------------------------------------------------------------------------------

def domain_summary(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in cookies:
        d = registrable_domain(c["domain"])
        e = out.setdefault(d, {"cookies": 0, "earliest_expiry": None, "local_storage": False})
        e["cookies"] += 1
        if c["expires"] != -1:
            iso = _iso(c["expires"])
            if e["earliest_expiry"] is None or iso < e["earliest_expiry"]:
                e["earliest_expiry"] = iso
    for origin in local_storage:
        host = origin.split("://", 1)[-1].split("/")[0].split(":")[0]
        d = registrable_domain(host)
        out.setdefault(d, {"cookies": 0, "earliest_expiry": None, "local_storage": False})["local_storage"] = True
    return out


def filter_domains(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]], exclude: list[str]) -> tuple[list, dict, list[str]]:
    ex = {registrable_domain(d) for d in exclude}
    kept = [c for c in cookies if registrable_domain(c["domain"]) not in ex]
    ls = {o: v for o, v in local_storage.items() if registrable_domain(o.split("://", 1)[-1].split("/")[0].split(":")[0]) not in ex}
    return kept, ls, sorted(ex)


def to_netscape(cookies: list[dict[str, Any]]) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        dom = c["domain"]
        prefix = "#HttpOnly_" if c["httpOnly"] else ""
        sub = "TRUE" if dom.startswith(".") else "FALSE"
        exp = int(c["expires"]) if c["expires"] > 0 else 0
        lines.append(f"{prefix}{dom}\t{sub}\t{c['path']}\t{'TRUE' if c['secure'] else 'FALSE'}\t{exp}\t{c['name']}\t{c['value']}")
    return "\n".join(lines) + "\n"


def to_storage_state(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]], domains: list[str]) -> dict[str, Any]:
    dset = {registrable_domain(d) for d in domains}
    cs = [{k: c[k] for k in COOKIE_KEYS if k in c and not (k == "sameSite" and c[k] is None)} | ({"sameSite": c["sameSite"] or "Lax"})
          for c in cookies if registrable_domain(c["domain"]) in dset]
    origins = [{"origin": o, "localStorage": [{"name": k, "value": v} for k, v in items.items()]}
               for o, items in local_storage.items() if registrable_domain(o.split("://", 1)[-1].split("/")[0].split(":")[0]) in dset]
    return {"cookies": cs, "origins": origins}


def redacted(cookies: list[dict[str, Any]]) -> dict[str, Any]:
    """Safe-to-print view: counts, domains and expiry dates only."""
    return {"cookies": len(cookies), "domains": len({registrable_domain(c["domain"]) for c in cookies})}

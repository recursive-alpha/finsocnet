"""Remote side of the session bridge: import, reapply, status, verify, purge (docs/spec/04 §4).

Cookie and storage values are handled only here and in `formats`/`bundle`; results contain counts, domain names and
dates, never values (secret-leak test: tests/integration/test_sessions.py)."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Protocol

import pyrage
from pyrage import x25519

from finsocnet.core import browser, config
from finsocnet.core.db import transaction
from finsocnet.core.ids import utc_now
from finsocnet.core.output import CliError
from finsocnet.core.sessions import bundle, formats, probes


def sessions_dir() -> Path:
    return config.data_dir() / "sessions"


def identity_path() -> Path:
    return Path(os.getenv("AGE_IDENTITY_FILE", bundle.DEFAULT_IDENTITY)).expanduser()


class Sink(Protocol):
    """Where cookies go: the agent browser (CdpSink) or a fake in tests."""
    def set_cookies(self, cookies: list[dict[str, Any]]) -> None: ...
    def set_local_storage(self, origin: str, items: dict[str, str]) -> None: ...
    def cookie_names(self) -> dict[str, set[str]]: ...
    def local_storage_keys(self, platform: str) -> set[str]: ...
    def delete_domains(self, domains: list[str] | None) -> None: ...
    def fetch(self, platform: str, url: str) -> tuple[str, str]: ...


class CdpSink:
    """Injects into the agent Chrome's default context (equivalent of CDP `Storage.setCookies`)."""

    def __init__(self) -> None:
        self.pw, self.browser, self.ctx = browser.attach()

    def close(self) -> None:
        self.pw.stop()

    def _cdp(self) -> Any:
        if not hasattr(self, "_session"):
            self._session = self.browser.new_browser_cdp_session()
        return self._session

    def set_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """CDP `Storage.setCookies` on the browser target (the default browser context)."""
        for i in range(0, len(cookies), 200):
            batch = []
            for c in cookies[i:i + 200]:
                item = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"], "secure": c["secure"], "httpOnly": c["httpOnly"]}
                if c["expires"] > 0:
                    item["expires"] = c["expires"]
                if c.get("sameSite") in ("Strict", "Lax", "None"):
                    item["sameSite"] = c["sameSite"]
                batch.append(item)
            try:
                self._cdp().send("Storage.setCookies", {"cookies": batch})
            except Exception:  # noqa: BLE001 - one malformed cookie must not lose the batch
                for item in batch:
                    try:
                        self._cdp().send("Storage.setCookies", {"cookies": [item]})
                    except Exception:  # noqa: BLE001
                        pass

    def set_local_storage(self, origin: str, items: dict[str, str]) -> None:
        pg = self.ctx.new_page()
        try:
            pg.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body="<html></html>"))
            pg.goto(origin.rstrip("/") + "/", wait_until="domcontentloaded")
            pg.evaluate("items => { for (const [k, v] of Object.entries(items)) localStorage.setItem(k, v); }", items)
        finally:
            pg.close()

    def cookie_names(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for c in self._cdp().send("Storage.getCookies").get("cookies", []):
            out.setdefault(formats.registrable_domain(c["domain"]), set()).add(c["name"])
        return out

    def local_storage_keys(self, platform: str) -> set[str]:
        cfg = browser.platforms().get(platform, {})
        keys: set[str] = set()
        if not cfg.get("local_storage_keys"):
            return keys
        for dom in cfg.get("domains", []):
            pg = self.ctx.new_page()
            try:
                pg.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body="<html></html>"))
                pg.goto(f"https://{dom}/", wait_until="domcontentloaded")
                keys |= set(pg.evaluate("Object.keys(localStorage)"))
            except Exception:  # noqa: BLE001
                pass
            finally:
                pg.close()
        return keys

    def delete_domains(self, domains: list[str] | None) -> None:
        if domains is None:
            self._cdp().send("Storage.clearCookies")
            return
        for c in self._cdp().send("Storage.getCookies").get("cookies", []):
            if formats.registrable_domain(c["domain"]) in domains:
                self._cdp().send("Network.deleteCookies", {"name": c["name"], "domain": c["domain"], "path": c["path"]})

    def fetch(self, platform: str, url: str) -> tuple[str, str]:
        pg = self.ctx.new_page()
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                text = pg.inner_text("body", timeout=3000)
            except Exception:  # noqa: BLE001
                text = pg.content()
            return pg.url, text
        finally:
            pg.close()


# --- the encrypted store -------------------------------------------------------------------------------

def _own_recipient() -> x25519.Recipient:
    return bundle.load_identity(identity_path()).to_public()


def load_store() -> dict[str, Any]:
    p = sessions_dir() / "store.age"
    if not p.exists():
        return {"cookies": [], "local_storage": {}}
    data = json.loads(pyrage.decrypt(p.read_bytes(), [bundle.load_identity(identity_path())]))
    return {"cookies": [formats.norm_cookie(c) for c in data.get("cookies", [])], "local_storage": data.get("local_storage", {})}


def save_store(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]]) -> None:
    d = sessions_dir()
    d.mkdir(parents=True, exist_ok=True)
    blob = pyrage.encrypt(json.dumps({"cookies": cookies, "local_storage": local_storage}).encode(), [_own_recipient()])
    p = d / "store.age"
    p.write_bytes(blob)
    p.chmod(0o600)


def _write_plain_files(cookies: list[dict[str, Any]], local_storage: dict[str, dict[str, str]]) -> None:
    """cookies.txt (yt-dlp) and storage/<platform>.json (Playwright format), chmod 600."""
    d = sessions_dir()
    (d / "storage").mkdir(parents=True, exist_ok=True)
    (d / "storage").chmod(0o700)
    p = d / "cookies.txt"
    p.write_text(formats.to_netscape(cookies), encoding="utf-8")
    p.chmod(0o600)
    for name, cfg in browser.platforms().items():
        state = formats.to_storage_state(cookies, local_storage, cfg.get("domains", []))
        f = d / "storage" / f"{name}.json"
        if state["cookies"] or state["origins"]:
            f.write_text(json.dumps(state), encoding="utf-8")
            f.chmod(0o600)
        elif f.exists():
            f.unlink()


def secure_delete(path: Path) -> None:
    """Overwrite files with zeros, then unlink; folders recursively."""
    if path.is_dir():
        for p in sorted(path.rglob("*"), reverse=True):
            secure_delete(p) if p.is_file() else p.rmdir()
        path.rmdir()
        return
    try:
        size = path.stat().st_size
        with open(path, "r+b") as fh:
            fh.write(b"\0" * size)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        pass
    path.unlink(missing_ok=True)


# --- commands -------------------------------------------------------------------------------------------

def load_input(path: Path, include_history: bool = True) -> dict[str, Any]:
    if path.is_file() and path.suffix == ".bundle":
        if not identity_path().exists():
            raise CliError("USAGE", f"no age identity at {identity_path()}", "run `session_bridge.py keygen` first")
        try:
            data = bundle.read_bundle(path.read_bytes(), identity_path())
        except Exception as e:  # noqa: BLE001 - wrong key or corrupt file; never echo content
            raise CliError("VALIDATION_ERROR", f"cannot decrypt {path.name}: {type(e).__name__}", "was the bundle encrypted to this host's recipient?") from e
        return {"bundle_id": data["manifest"]["bundle_id"], "cookies": data["cookies"], "local_storage": data["local_storage"],
                "history": data["history"], "files": []}
    if not path.exists():
        raise CliError("NOT_FOUND", f"{path} does not exist")
    scan = formats.scan_dir(path, include_history)
    if any(f["kind"] == "chrome_cookies" for f in scan["files"]) and not scan["cookies"]:
        raise CliError("VALIDATION_ERROR", "this folder holds an encrypted Chrome profile the remote cannot decrypt",
                       "export locally instead: finsocnet session export && finsocnet session push")
    from finsocnet.core import ids
    return {"bundle_id": ids.bundle_id(), "cookies": scan["cookies"], "local_storage": scan["local_storage"], "history": scan["history"], "files": scan["files"]}


def import_session(conn: sqlite3.Connection, path: Path, run_id: int, sink: Sink, verify: bool = True) -> dict[str, Any]:
    inp = load_input(path)
    cookies, dropped = formats.drop_expired(inp["cookies"])
    sink.set_cookies(cookies)
    for origin, items in inp["local_storage"].items():
        sink.set_local_storage(origin, items)

    merged_store = load_store() if (sessions_dir() / "store.age").exists() else {"cookies": [], "local_storage": {}}
    all_cookies = formats.merge_cookies(merged_store["cookies"] + cookies)
    all_ls = {**merged_store["local_storage"]}
    for origin, items in inp["local_storage"].items():
        all_ls.setdefault(origin, {}).update(items)
    save_store(all_cookies, all_ls)
    _write_plain_files(all_cookies, all_ls)

    summary = formats.domain_summary(cookies, inp["local_storage"])
    now = utc_now()
    with transaction(conn):
        for dom, s in summary.items():
            conn.execute(
                "INSERT INTO browser_sessions (domain, platform, cookie_count, earliest_expiry, has_local_storage, bundle_id, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (domain) DO UPDATE SET platform = excluded.platform, cookie_count = excluded.cookie_count, earliest_expiry = excluded.earliest_expiry, "
                "has_local_storage = excluded.has_local_storage, bundle_id = excluded.bundle_id, imported_at = excluded.imported_at, login_state = 'unknown', verified_at = NULL",
                (dom, browser.platform_for_domain(dom), s["cookies"], s["earliest_expiry"], int(s["local_storage"]), inp["bundle_id"], now))
        for h in inp["history"]:
            conn.execute("INSERT INTO history_entries (url, title, visit_count, last_visit_at, bundle_id) VALUES (?, ?, ?, ?, ?) "
                         "ON CONFLICT (url) DO UPDATE SET title = excluded.title, visit_count = excluded.visit_count, last_visit_at = excluded.last_visit_at",
                         (h["url"], h.get("title"), h.get("visit_count"), h.get("last_visit_at"), inp["bundle_id"]))

    if path.exists():
        secure_delete(path)
    platforms = verify_all(conn, sink) if verify else status(conn, sink)["platforms"]
    return {"bundle_id": inp["bundle_id"], "cookies_imported": len(cookies), "cookies_expired_dropped": dropped, "domains": len(summary),
            "local_storage_origins": len(inp["local_storage"]), "history_entries": len(inp["history"]), "platforms": platforms}


def _platform_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM browser_sessions WHERE platform IS NOT NULL ORDER BY platform, domain").fetchall()


def status(conn: sqlite3.Connection, sink: Sink | None = None, platform: str | None = None) -> dict[str, Any]:
    live: dict[str, set[str]] = {}
    if sink is not None:
        try:
            live = sink.cookie_names()
        except Exception:  # noqa: BLE001
            live = {}
    rows = [dict(r) for r in _platform_rows(conn) if platform in (None, r["platform"])]
    for r in rows:
        r["live_cookies"] = len(live.get(r["domain"], ())) if sink is not None else None
    total = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(cookie_count), 0) AS c FROM browser_sessions").fetchone()
    return {"platforms": [{k: r[k] for k in ("platform", "domain", "cookie_count", "earliest_expiry", "has_local_storage", "login_state", "verified_at", "imported_at", "live_cookies")} for r in rows],
            "domains_total": total["n"], "cookies_total": total["c"]}


def verify(conn: sqlite3.Connection, sink: Sink, platform: str) -> dict[str, Any]:
    cfg = browser.platforms().get(platform)
    if cfg is None:
        raise CliError("USAGE", f"unknown platform {platform!r}", "see config/platforms.yaml")
    names = sink.cookie_names()
    scoped = {d: names.get(formats.registrable_domain(d), set()) for d in cfg.get("domains", [])}
    state = probes.login_state(platform, scoped, sink.local_storage_keys(platform), lambda url: sink.fetch(platform, url))
    now = utc_now()
    with transaction(conn):
        for d in cfg.get("domains", []):
            conn.execute("UPDATE browser_sessions SET login_state = ?, verified_at = ? WHERE domain = ?", (state, now, formats.registrable_domain(d)))
    return {"platform": platform, "login_state": state}


def verify_all(conn: sqlite3.Connection, sink: Sink) -> list[dict[str, Any]]:
    seen = []
    for r in _platform_rows(conn):
        if r["platform"] not in seen:
            seen.append(r["platform"])
            try:
                verify(conn, sink, r["platform"])
            except CliError:
                pass
    return status(conn, sink)["platforms"]


def reapply(sink: Sink) -> dict[str, Any]:
    """Re-inject the stored session cookies and localStorage (session cookies vanish when Chrome restarts)."""
    store = load_store()
    cookies, dropped = formats.drop_expired(store["cookies"])
    sink.set_cookies(cookies)
    for origin, items in store["local_storage"].items():
        try:
            sink.set_local_storage(origin, items)
        except Exception:  # noqa: BLE001
            pass
    return {"cookies_applied": len(cookies), "cookies_expired_dropped": dropped, "local_storage_origins": len(store["local_storage"])}


def purge(conn: sqlite3.Connection, sink: Sink | None, domains: list[str] | None) -> dict[str, Any]:
    """Remove sessions from the browser, the encrypted store, the plain files and the metadata. `domains=None` = all."""
    targets = None if domains is None else sorted({formats.registrable_domain(d) for d in domains})
    store = load_store() if (sessions_dir() / "store.age").exists() else {"cookies": [], "local_storage": {}}
    if targets is None:
        keep_c, keep_ls = [], {}
    else:
        keep_c = [c for c in store["cookies"] if formats.registrable_domain(c["domain"]) not in targets]
        keep_ls = {o: v for o, v in store["local_storage"].items() if formats.registrable_domain(o.split("://", 1)[-1].split("/")[0].split(":")[0]) not in targets}
    removed = len(store["cookies"]) - len(keep_c)
    if sink is not None:
        sink.delete_domains(targets)
    if targets is None and (sessions_dir() / "store.age").exists():
        (sessions_dir() / "store.age").unlink()
    else:
        save_store(keep_c, keep_ls)
    _write_plain_files(keep_c, keep_ls)
    if targets is None and (sessions_dir() / "cookies.txt").exists():
        (sessions_dir() / "cookies.txt").unlink()
    with transaction(conn):
        if targets is None:
            conn.execute("DELETE FROM browser_sessions")
        else:
            conn.executemany("DELETE FROM browser_sessions WHERE domain = ?", [(d,) for d in targets])
    return {"domains": targets if targets is not None else "all", "cookies_removed": removed}

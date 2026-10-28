"""Session bridge: formats, bundles, import/reapply/purge, secret-leak test, login probes, budgets (specs/04, 00 §10)."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from finsocnet.core import browser, browser_proc, budgets, config
from finsocnet.core.output import CliError
from finsocnet.core.sessions import bundle, formats, import_remote, probes

SECRET = "SECRETVALUE-9f8e7d"
FUTURE = datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()
PAST = 1_000_000_000.0


def cookie(name="auth_token", domain=".x.com", value=SECRET, expires=FUTURE, **kw):
    return formats.norm_cookie({"name": name, "value": value, "domain": domain, "path": "/", "expires": expires, "secure": True, "httpOnly": True, "sameSite": "Lax", **kw})


class FakeSink:
    def __init__(self):
        self.cookies, self.ls, self.deleted = [], {}, []
        self.pages = {}

    def set_cookies(self, cookies): self.cookies += cookies
    def set_local_storage(self, origin, items): self.ls[origin] = items
    def cookie_names(self):
        out = {}
        for c in self.cookies:
            out.setdefault(formats.registrable_domain(c["domain"]), set()).add(c["name"])
        return out
    def local_storage_keys(self, platform):
        return {k for o, v in self.ls.items() for k in v}
    def delete_domains(self, domains):
        self.deleted.append(domains)
        self.cookies = [] if domains is None else [c for c in self.cookies if formats.registrable_domain(c["domain"]) not in domains]
    def fetch(self, platform, url):
        return self.pages.get(platform, (url, "Home timeline"))


@pytest.fixture
def identity(tmp_path, monkeypatch):
    path = tmp_path / "keys" / "age_identity.txt"
    recipient = bundle.generate_identity(path)
    monkeypatch.setenv("AGE_IDENTITY_FILE", str(path))
    return path, recipient


# --- formats ---------------------------------------------------------------------------------------------

def test_every_format_is_detected_by_content_and_parsed(tmp_path):
    netscape = tmp_path / "a.dat"
    netscape.write_text(f"# Netscape HTTP Cookie File\n.x.com\tTRUE\t/\tTRUE\t1893456000\tauth_token\t{SECRET}\n#HttpOnly_.reddit.com\tTRUE\t/\tTRUE\t0\treddit_session\t{SECRET}\n")
    editor = tmp_path / "b.txt"
    editor.write_text(json.dumps([{"name": "sid", "value": SECRET, "domain": ".medium.com", "path": "/", "expirationDate": 1893456000, "sameSite": "no_restriction", "secure": True, "httpOnly": False}]))
    state = tmp_path / "c.bin"
    state.write_text(json.dumps({"cookies": [{"name": "c_user", "value": SECRET, "domain": ".facebook.com", "path": "/", "expires": 1893456000, "httpOnly": True, "secure": True, "sameSite": "Lax"}],
                                 "origins": [{"origin": "https://discord.com", "localStorage": [{"name": "token", "value": SECRET}]}]}))
    har = tmp_path / "d.har"
    har.write_text(json.dumps({"log": {"entries": [{"request": {"url": "https://substack.com/x", "cookies": []}, "response": {"cookies": [{"name": "substack.sid", "value": SECRET}]}}]}}))
    ff = tmp_path / "cookies.sqlite"
    c = sqlite3.connect(ff)
    c.execute("CREATE TABLE moz_cookies (name TEXT, value TEXT, host TEXT, path TEXT, expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER, sameSite INTEGER)")
    c.execute("INSERT INTO moz_cookies VALUES ('sessionid', ?, '.tradingview.com', '/', 1893456000, 1, 1, 1)", (SECRET,))
    c.commit(); c.close()
    kinds = {p.name: formats.detect(p) for p in (netscape, editor, state, har, ff)}
    assert kinds == {"a.dat": "netscape", "b.txt": "cookie_editor", "c.bin": "storage_state", "d.har": "har", "cookies.sqlite": "firefox_cookies"}

    scan = formats.scan_dir(tmp_path)
    names = {(c["name"], formats.registrable_domain(c["domain"])) for c in scan["cookies"]}
    assert {("auth_token", "x.com"), ("reddit_session", "reddit.com"), ("sid", "medium.com"), ("c_user", "facebook.com"), ("substack.sid", "substack.com"), ("sessionid", "tradingview.com")} <= names
    assert scan["local_storage"]["https://discord.com"]["token"] == SECRET
    assert all(SECRET not in json.dumps(f) for f in scan["files"])  # the per-file report holds counts only
    ed = next(c for c in scan["cookies"] if c["name"] == "sid")
    assert ed["sameSite"] == "None" and ed["httpOnly"] is False
    assert next(c for c in scan["cookies"] if c["name"] == "reddit_session")["httpOnly"] is True


def test_merge_newest_expiry_wins_and_expired_dropped():
    old, new = cookie(expires=FUTURE - 1000, value="old"), cookie(expires=FUTURE, value="new")
    merged = formats.merge_cookies([old, new])
    assert len(merged) == 1 and merged[0]["value"] == "new"
    kept, dropped = formats.drop_expired([cookie(expires=PAST), cookie(name="s", expires=-1), cookie(name="t")])
    assert dropped == 1 and {c["name"] for c in kept} == {"s", "t"}


def test_registrable_domain_and_summary():
    assert formats.registrable_domain(".www.example.co.uk") == "example.co.uk"
    assert formats.registrable_domain("api.x.com") == "x.com"
    s = formats.domain_summary([cookie(), cookie(name="ct0"), cookie(name="sid", domain=".medium.com", expires=-1)], {"https://discord.com": {"token": "t"}})
    assert s["x.com"]["cookies"] == 2 and s["medium.com"]["earliest_expiry"] is None and s["discord.com"]["local_storage"] is True


def test_exclude_domains():
    cs, ls, ex = formats.filter_domains([cookie(), cookie(name="n", domain=".bank.com")], {"https://bank.com": {"a": "b"}}, ["bank.com"])
    assert [c["name"] for c in cs] == ["auth_token"] and ls == {} and ex == ["bank.com"]


# --- bundle ----------------------------------------------------------------------------------------------

def test_bundle_roundtrip_is_encrypted_and_wrong_key_fails(tmp_path, identity):
    path, recipient = identity
    data, manifest = bundle.build_bundle([cookie()], {"https://discord.com": {"token": SECRET}}, [{"url": "https://x.com", "title": "X", "visit_count": 3}],
                                         recipient, {"browser": "chrome", "method": "A"}, [])
    assert SECRET.encode() not in data and manifest["counts"] == {"cookies": 1, "domains": 2, "local_storage_origins": 1, "history_entries": 1}
    out = bundle.read_bundle(data, path)
    assert out["cookies"][0]["value"] == SECRET and out["local_storage"]["https://discord.com"]["token"] == SECRET and out["history"][0]["visit_count"] == 3
    other = tmp_path / "other.txt"
    bundle.generate_identity(other)
    with pytest.raises(Exception):
        bundle.read_bundle(data, other)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


# --- import, store, secret-leak, reapply, purge ----------------------------------------------------------

def make_bundle(tmp_path, recipient, cookies=None, ls=None, history=None):
    data, manifest = bundle.build_bundle(cookies or [cookie(), cookie(name="ct0", value=SECRET + "-ct0"), cookie(name="gone", expires=PAST),
                                                    cookie(name="reddit_session", domain=".reddit.com"), cookie(name="token_v2", domain=".reddit.com")],
                                         ls if ls is not None else {"https://discord.com": {"token": SECRET + "-discord"}}, history or [], recipient, {"browser": "chrome"}, [])
    inbox = config.data_dir() / "sessions" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"{manifest['bundle_id']}.bundle"
    path.write_bytes(data)
    return path


def test_import_persists_metadata_only_and_never_leaks_values(conn, run_id, identity, tmp_path, capsys, caplog):
    _, recipient = identity
    sink = FakeSink()
    sink.pages["x"] = ("https://x.com/home", "Home")
    sink.pages["reddit"] = ("https://www.reddit.com/api/me.json", json.dumps({"data": {"name": "me"}}))
    path = make_bundle(tmp_path, recipient, history=[{"url": "https://x.com/qullamaggie", "title": "Q", "visit_count": 5, "last_visit_at": "2026-10-01T00:00:00Z"}])
    res = import_remote.import_session(conn, path, run_id, sink)
    assert res["cookies_imported"] == 4 and res["cookies_expired_dropped"] == 1 and res["history_entries"] == 1
    states = {p["platform"]: p["login_state"] for p in res["platforms"]}
    assert states["x"] == "logged_in" and states["reddit"] == "logged_in" and states["discord"] == "logged_in"  # token key in localStorage
    assert not path.exists()  # the inbox input is securely deleted

    rows = {r["domain"]: dict(r) for r in conn.execute("SELECT * FROM browser_sessions")}
    assert rows["x.com"]["cookie_count"] == 2 and rows["x.com"]["platform"] == "x" and rows["discord.com"]["has_local_storage"] == 1
    assert conn.execute("SELECT triage FROM history_entries").fetchone()[0] == "pending"

    # secret-leak test: values must not appear in stdout, stderr, logs, the DB file, data/work, or the encrypted store
    out = capsys.readouterr()
    blob = json.dumps(res) + out.out + out.err + caplog.text
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    blob_bytes = Path(config.db_path()).read_bytes() + (config.data_dir() / "sessions" / "store.age").read_bytes()
    assert SECRET not in blob and SECRET.encode() not in blob_bytes
    work = config.data_dir() / "work"
    assert not work.exists() or not any(SECRET in p.read_text(errors="ignore") for p in work.rglob("*") if p.is_file())
    st = import_remote.status(conn, sink)
    assert SECRET not in json.dumps(st)

    # plaintext helper files exist with chmod 600 and are regenerated from the store
    cj = config.data_dir() / "sessions" / "cookies.txt"
    assert stat.S_IMODE(cj.stat().st_mode) == 0o600 and SECRET in cj.read_text()
    xs = config.data_dir() / "sessions" / "storage" / "x.json"
    assert stat.S_IMODE(xs.stat().st_mode) == 0o600 and json.loads(xs.read_text())["cookies"]


def test_reapply_restores_session_cookies_after_a_browser_restart(conn, run_id, identity, tmp_path):
    _, recipient = identity
    sink = FakeSink()
    import_remote.import_session(conn, make_bundle(tmp_path, recipient, [cookie(name="sess", expires=-1), cookie()], {}), run_id, sink, verify=False)
    fresh = FakeSink()  # "restarted" browser lost everything
    res = import_remote.reapply(fresh)
    assert res["cookies_applied"] == 2 and {c["name"] for c in fresh.cookies} == {"sess", "auth_token"}


def test_purge_removes_cookies_store_files_and_metadata(conn, run_id, identity, tmp_path):
    _, recipient = identity
    sink = FakeSink()
    import_remote.import_session(conn, make_bundle(tmp_path, recipient), run_id, sink, verify=False)
    out = import_remote.purge(conn, sink, ["x.com"])
    assert out["cookies_removed"] == 2 and conn.execute("SELECT COUNT(*) FROM browser_sessions WHERE domain = 'x.com'").fetchone()[0] == 0
    assert "auth_token" not in {c["name"] for c in import_remote.load_store()["cookies"]}
    assert not (config.data_dir() / "sessions" / "storage" / "x.json").exists()
    import_remote.purge(conn, sink, None)
    assert not (config.data_dir() / "sessions" / "store.age").exists() and conn.execute("SELECT COUNT(*) FROM browser_sessions").fetchone()[0] == 0


def test_chrome_profile_folder_is_refused_with_a_hint(conn, run_id, identity, tmp_path):
    d = tmp_path / "profile"
    d.mkdir()
    c = sqlite3.connect(d / "Cookies")
    c.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB)")
    c.commit(); c.close()
    with pytest.raises(CliError) as e:
        import_remote.import_session(conn, d, run_id, FakeSink(), verify=False)
    assert "export locally" in e.value.hint


# --- probes and checkpoints --------------------------------------------------------------------------------

class FakePage:
    def __init__(self, url, text): self.url, self._t = url, text
    def inner_text(self, sel, timeout=0): return self._t


def test_logged_out_and_checkpoint_pages_raise_exit_3(repo):
    with pytest.raises(CliError) as e:
        browser.check_page("x", FakePage("https://x.com/i/flow/login", "Sign in"))
    assert e.value.code == "LOGIN_REQUIRED" and "finsocnet session export" in e.value.hint
    with pytest.raises(CliError) as e:
        browser.check_page("facebook", FakePage("https://www.facebook.com/checkpoint/123", "Confirm your identity"))
    assert e.value.code == "CHECKPOINT"
    browser.check_page("x", FakePage("https://x.com/home", "Home timeline"))  # no error
    from finsocnet.core.output import EXIT_CODES
    assert EXIT_CODES["LOGIN_REQUIRED"] == EXIT_CODES["CHECKPOINT"] == 3


def test_probe_states(repo):
    names = {"x.com": {"auth_token", "ct0"}}
    assert probes.login_state("x", names, set(), lambda u: ("https://x.com/home", "Home")) == "logged_in"
    assert probes.login_state("x", names, set(), lambda u: ("https://x.com/i/flow/login", "")) == "logged_out"
    assert probes.login_state("facebook", {"facebook.com": {"c_user", "xs"}}, set(), lambda u: ("https://www.facebook.com/checkpoint/1", "")) == "checkpoint"
    assert probes.login_state("x", {"x.com": {"ct0"}}, set(), lambda u: ("https://x.com/home", "")) == "logged_out"  # session cookie missing
    assert probes.login_state("reddit", {"reddit.com": {"reddit_session", "token_v2"}}, set(), lambda u: (u, json.dumps({"data": {"name": ""}}))) == "logged_out"
    assert probes.login_state("discord", {}, {"token"}, lambda u: ("https://discord.com/channels/@me", "ok")) == "logged_in"


# --- budgets ---------------------------------------------------------------------------------------------

def test_budget_exhaustion_returns_exit_4_with_retry_after(conn, repo):
    (repo / "config" / "budgets.yaml").write_text("default: {per_minute: 2, per_hour: 100, per_day: 1000, min_delay_ms: 1, max_delay_ms: 2}\n")
    budgets._load.cache_clear()
    now = datetime(2026, 10, 28, 9, 15, 30, tzinfo=timezone.utc)
    assert budgets.charge(conn, "x", now=now) == {"minute": 1, "hour": 99, "day": 999}
    budgets.charge(conn, "x", now=now)
    with pytest.raises(CliError) as e:
        budgets.charge(conn, "x", now=now)
    assert e.value.code == "BUDGET_EXHAUSTED" and 29 <= e.value.retry_after_sec <= 32
    from finsocnet.core.output import EXIT_CODES
    assert EXIT_CODES["BUDGET_EXHAUSTED"] == 4 and budgets.exhausted(conn, "x", now)
    assert not budgets.exhausted(conn, "reddit", now)
    later = datetime(2026, 10, 28, 9, 16, 1, tzinfo=timezone.utc)  # next minute window
    budgets.charge(conn, "x", now=later)
    budgets._load.cache_clear()


# --- the real agent browser (local headless Chromium, no network) ----------------------------------------

def _chrome_available() -> bool:
    try:
        browser_proc.find_chrome()
        return True
    except CliError:
        return False


@pytest.mark.skipif(not _chrome_available(), reason="no Chrome/Chromium binary")
def test_agent_browser_import_survives_restart(conn, run_id, identity, tmp_path, monkeypatch):
    _, recipient = identity
    port = 19300 + os.getpid() % 500
    monkeypatch.setenv("CDP_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("BROWSER_PROFILE_DIR", str(tmp_path / "profile"))
    try:
        assert browser_proc.start(headless=True)["state"] == "started"
        assert browser_proc.start(headless=True)["state"] == "already_running"  # idempotent
        sink = import_remote.CdpSink()
        try:
            path = make_bundle(tmp_path, recipient, [cookie(name="auth_token", domain=".example.com"), cookie(name="sess", domain=".example.com", expires=-1)], {})
            res = import_remote.import_session(conn, path, run_id, sink, verify=False)
            assert res["cookies_imported"] == 2
            live = sink.cookie_names()
            assert live["example.com"] == {"auth_token", "sess"}  # CDP cookie names per domain
        finally:
            sink.close()
        browser_proc.stop()
        monkeypatch.setenv("BROWSER_PROFILE_DIR", str(tmp_path / "profile2"))  # a fresh profile loses session cookies
        browser_proc.start(headless=True)
        sink = import_remote.CdpSink()
        try:
            assert "example.com" not in sink.cookie_names()
            assert import_remote.reapply(sink)["cookies_applied"] == 2
            assert sink.cookie_names()["example.com"] == {"auth_token", "sess"}
        finally:
            sink.close()
    finally:
        browser_proc.stop()


def test_browser_unavailable_exit_7(monkeypatch):
    monkeypatch.setenv("CDP_URL", "http://127.0.0.1:1")
    with pytest.raises(CliError) as e:
        browser.attach()
    assert e.value.code == "BROWSER_UNAVAILABLE"
    from finsocnet.core.output import EXIT_CODES
    assert EXIT_CODES["BROWSER_UNAVAILABLE"] == 7


def test_launch_flags_never_include_automation():
    cmd = browser_proc.build_command("/usr/bin/chrome", headless=False, proxy="socks5://127.0.0.1:1080")
    joined = " ".join(cmd)
    assert "--remote-debugging-address=127.0.0.1" in joined and "--proxy-server=socks5://127.0.0.1:1080" in joined and "--headless" not in joined
    assert not any(f in joined for f in browser_proc.FORBIDDEN_FLAGS)

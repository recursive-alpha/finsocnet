"""Local side of the session bridge: collect cookies from the user's browser and write an encrypted bundle
(docs/spec/04 §3). Methods are tried in order: A (copy the profile and let the same Chrome decrypt it over CDP),
B (rookiepy), C (ask the user for an extension export). Only counts are ever printed."""

from __future__ import annotations

import os
import platform as _platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

from finsocnet.core import browser, ids
from finsocnet.core.output import CliError
from finsocnet.core.sessions import bundle, formats

CONFIG_DIR = Path("~/.config/finsocnet").expanduser()
REMOTE_TOML = CONFIG_DIR / "remote.toml"
BUNDLE_DIR = Path("~/.local/share/finsocnet/bundles").expanduser()

CHROME_ROOTS = {
    "linux": {"chrome": "~/.config/google-chrome", "chromium": "~/.config/chromium", "brave": "~/.config/BraveSoftware/Brave-Browser", "edge": "~/.config/microsoft-edge"},
    "darwin": {"chrome": "~/Library/Application Support/Google/Chrome", "chromium": "~/Library/Application Support/Chromium",
               "brave": "~/Library/Application Support/BraveSoftware/Brave-Browser", "edge": "~/Library/Application Support/Microsoft Edge"},
    "windows": {"chrome": "~/AppData/Local/Google/Chrome/User Data", "chromium": "~/AppData/Local/Chromium/User Data",
                "brave": "~/AppData/Local/BraveSoftware/Brave-Browser/User Data", "edge": "~/AppData/Local/Microsoft/Edge/User Data"},
}
FIREFOX_ROOTS = {"linux": "~/.mozilla/firefox", "darwin": "~/Library/Application Support/Firefox/Profiles", "windows": "~/AppData/Roaming/Mozilla/Firefox/Profiles"}


def os_name() -> str:
    s = sys.platform
    return "windows" if s.startswith("win") else "darwin" if s == "darwin" else "linux"


def init_local(recipient: str, remote: str, remote_path: str) -> dict[str, Any]:
    from pyrage import x25519
    try:
        x25519.Recipient.from_str(recipient)
    except Exception as e:  # noqa: BLE001
        raise CliError("VALIDATION_ERROR", "recipient is not a valid age public key (age1…)") from e
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    REMOTE_TOML.write_text(f'recipient = "{recipient}"\nremote = "{remote}"\nremote_path = "{remote_path}"\n', encoding="utf-8")
    REMOTE_TOML.chmod(0o600)
    return {"config": str(REMOTE_TOML), "remote": remote, "remote_path": remote_path}


def load_config() -> dict[str, str]:
    if not REMOTE_TOML.exists():
        raise CliError("USAGE", "no remote configured", "run `finsocnet session init-local --recipient age1… --remote user@host --remote-path /srv/finsocnet`")
    return tomllib.loads(REMOTE_TOML.read_text(encoding="utf-8"))


def find_profile(browser_name: str, profile: str) -> tuple[Path, str]:
    osn = os_name()
    if browser_name == "firefox":
        root = Path(FIREFOX_ROOTS[osn]).expanduser()
        cands = sorted(root.glob(f"*{profile}*")) if profile != "Default" else sorted(root.glob("*.default*"))
        if not cands:
            raise CliError("NOT_FOUND", f"no Firefox profile under {root}")
        return cands[0], "firefox"
    root = Path(CHROME_ROOTS[osn][browser_name]).expanduser()
    p = root / profile
    if not p.exists():
        raise CliError("NOT_FOUND", f"{browser_name} profile {profile!r} not found under {root}", "pass --profile NAME or --from-dir PATH")
    return p, "chrome"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def method_a(profile: Path, chrome_bin: str, origins: list[str], extra_flags: list[str] | None = None) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], str]:
    """Copy the profile into a temp user-data-dir, start the same Chrome on it with a debugging port, read cookies over CDP."""
    tmp = Path(tempfile.mkdtemp(prefix="finsocnet-export-"))
    try:
        dest = tmp / "Default"
        dest.mkdir()
        for name in ("Cookies", "Network/Cookies", "Preferences", "Local Storage", "Network/Cookies-journal", "Cookies-journal"):
            src = profile / name
            if src.is_dir():
                shutil.copytree(src, dest / name, dirs_exist_ok=True)
            elif src.exists():
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest / name)
        ls_state = profile.parent / "Local State"
        if ls_state.exists():
            shutil.copy(ls_state, tmp / "Local State")
        port = free_port()
        proc = subprocess.Popen([chrome_bin, f"--user-data-dir={tmp}", f"--remote-debugging-port={port}", "--headless=new", "--no-first-run", "--no-sandbox", *(extra_flags or []), "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            try:
                b = None
                for _ in range(40):
                    try:
                        b = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                        break
                    except Exception:  # noqa: BLE001
                        time.sleep(0.5)
                if b is None:
                    raise CliError("BROWSER_UNAVAILABLE", "local Chrome did not start for the export")
                ctx = b.contexts[0]
                cookies = [formats.norm_cookie({**c, "expires": c.get("expires", -1)}) for c in ctx.cookies()]
                ls: dict[str, dict[str, str]] = {}
                for origin in origins:
                    pg = ctx.new_page()
                    try:
                        pg.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body="<html></html>"))
                        pg.goto(origin.rstrip("/") + "/", wait_until="domcontentloaded")
                        items = pg.evaluate("Object.fromEntries(Object.entries(localStorage))")
                        if items:
                            ls[origin] = items
                    except Exception:  # noqa: BLE001
                        pass
                    finally:
                        pg.close()
                return cookies, ls, "A"
            finally:
                pw.stop()
        finally:
            proc.terminate()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def method_b(browser_name: str) -> tuple[list[dict[str, Any]], str]:
    try:
        import rookiepy  # type: ignore[import-not-found]
    except ImportError as e:
        raise CliError("UNSUPPORTED", "rookiepy is not installed", "install the local extra: uv sync --extra local") from e
    fn = getattr(rookiepy, browser_name, None) or rookiepy.load
    return [formats.norm_cookie({**c, "expires": c.get("expires") or -1}) for c in fn()], "B"


def export(browser_name: str = "chrome", profile_name: str = "Default", from_dir: str | None = None, history: bool = False,
           exclude: list[str] | None = None, out: str | None = None, recipient: str | None = None) -> dict[str, Any]:
    recipient = recipient or load_config()["recipient"]
    cookies: list[dict[str, Any]] = []
    ls: dict[str, dict[str, str]] = {}
    hist: list[dict[str, Any]] = []
    method, files, version = "C", [], None
    if from_dir:
        scan = formats.scan_dir(Path(from_dir).expanduser(), history)
        cookies, ls, hist, files, method = scan["cookies"], scan["local_storage"], scan["history"], scan["files"], "dir"
    else:
        prof, family = find_profile(browser_name, profile_name)
        tried = []
        if family == "firefox":
            f = prof / "cookies.sqlite"
            cookies, method = (formats.parse_firefox_cookies(f), "firefox") if f.exists() else ([], "C")
            if history and (prof / "places.sqlite").exists():
                hist = formats.parse_history(prof / "places.sqlite", "firefox_history")
        else:
            try:
                origins = [f"https://{d}" for cfg in browser.platforms().values() if cfg.get("local_storage_keys") for d in cfg.get("domains", [])]
                cookies, ls, method = method_a(prof, _local_chrome(browser_name), origins, os.getenv("FINSOCNET_EXPORT_CHROME_FLAGS", "").split())
            except Exception as e:  # noqa: BLE001
                tried.append(f"A failed: {type(e).__name__}")
                try:
                    cookies, method = method_b(browser_name)
                except Exception as e2:  # noqa: BLE001
                    tried.append(f"B failed: {type(e2).__name__}")
                    raise CliError("UNSUPPORTED", "could not read the browser's cookies (" + "; ".join(tried) + ")",
                                   "method C: export cookies with the Cookie-Editor extension (JSON) into a folder and run `finsocnet session export --from-dir <folder>`") from e2
            if history and (prof / "History").exists():
                hist = formats.parse_history(prof / "History", "chrome_history")
    cookies, expired = formats.drop_expired(cookies)
    cookies, ls, excluded = formats.filter_domains(cookies, ls, exclude or [])
    if not cookies and not ls:
        raise CliError("VALIDATION_ERROR", "no cookies found", "log in in your browser first, or point --from-dir at a cookie export")
    source = {"browser": browser_name, "profile": profile_name, "os": os_name(), "method": method, "version": version,
              "user_agent": None, "locale": os.getenv("LANG", "en-US").split(".")[0].replace("_", "-"), "timezone": time.tzname[0]}
    data, manifest = bundle.build_bundle(cookies, ls, hist, recipient, source, excluded)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR.chmod(0o700)
    path = Path(out).expanduser() if out else BUNDLE_DIR / f"{manifest['bundle_id']}.bundle"
    path.write_bytes(data)
    path.chmod(0o600)
    return {"bundle": str(path), "bundle_id": manifest["bundle_id"], "method": method, "counts": manifest["counts"], "expired_dropped": expired,
            "excluded_domains": excluded, "files": files, "domains": {d: {"cookies": s["cookies"], "earliest_expiry": s["earliest_expiry"]} for d, s in manifest["domains"].items()}}


def _local_chrome(browser_name: str) -> str:
    names = {"chrome": ["google-chrome", "google-chrome-stable", "chrome"], "chromium": ["chromium", "chromium-browser"], "brave": ["brave-browser", "brave"], "edge": ["microsoft-edge"]}
    for n in names.get(browser_name, []):
        p = shutil.which(n)
        if p:
            return p
    mac = {"chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "chromium": "/Applications/Chromium.app/Contents/MacOS/Chromium",
           "brave": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"}
    if Path(mac.get(browser_name, "")).exists():
        return mac[browser_name]
    win = {"chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe"}
    if Path(win.get(browser_name, "")).exists():
        return win[browser_name]
    raise CliError("UNSUPPORTED", f"{browser_name} binary not found")


def newest_bundle() -> Path:
    files = sorted(BUNDLE_DIR.glob("*.bundle"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise CliError("NOT_FOUND", f"no bundles in {BUNDLE_DIR}", "run `finsocnet session export` first")
    return files[-1]


def push(file: str | None = None, run_import: bool = True) -> dict[str, Any]:
    cfg = load_config()
    path = Path(file).expanduser() if file else newest_bundle()
    remote_dir = f"{cfg['remote_path'].rstrip('/')}/data/sessions/inbox"
    subprocess.run(["ssh", cfg["remote"], f"mkdir -p {remote_dir} && chmod 700 {remote_dir}"], check=True, capture_output=True)
    subprocess.run(["scp", "-q", str(path), f"{cfg['remote']}:{remote_dir}/"], check=True, capture_output=True)
    result: dict[str, Any] = {"pushed": path.name, "remote": cfg["remote"]}
    if run_import:
        cmd = (f"cd {cfg['remote_path']} && uv run .agents/skills/session-bridge/scripts/session_bridge.py import data/sessions/inbox/{path.name}")
        r = subprocess.run(["ssh", cfg["remote"], cmd], capture_output=True, text=True)
        result["import_exit_code"] = r.returncode
        result["import_output"] = r.stdout.strip()[-4000:]
    return result

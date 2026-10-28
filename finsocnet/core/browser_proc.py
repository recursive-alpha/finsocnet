"""Start, stop and inspect the single agent Chrome (specs/04 §6.1–6.2). Launch flags are normative: no automation flags,
no user-agent override, headed under Xvfb unless `--headless` is passed for debugging."""

from __future__ import annotations

import glob
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from finsocnet.core import browser, config
from finsocnet.core.output import CliError

CHROME_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"]
FORBIDDEN_FLAGS = ("--enable-automation", "--disable-blink-features", "--user-agent")


def find_chrome() -> str:
    explicit = os.getenv("CHROME_BIN")
    if explicit:
        return explicit
    for name in CHROME_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    # Development fallback: the Chromium that Playwright downloaded.
    for pattern in ("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome", "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"):
        found = sorted(glob.glob(os.path.expanduser(pattern)))
        if found:
            return found[-1]
    raise CliError("UNSUPPORTED", "no Chrome/Chromium binary found", "install google-chrome or chromium, or set CHROME_BIN")


def pid_file() -> Path:
    return browser.profile_dir() / ".finsocnet.pid"


def cdp_port() -> int:
    return int(browser.cdp_url().rsplit(":", 1)[-1].split("/")[0])


def build_command(chrome: str, headless: bool = False, proxy: str | None = None, lang: str = "en-US") -> list[str]:
    cmd = [chrome, f"--user-data-dir={browser.profile_dir()}", "--remote-debugging-address=127.0.0.1", f"--remote-debugging-port={cdp_port()}",
           "--no-first-run", "--no-default-browser-check", "--window-size=1366,900", f"--lang={lang}"]
    if sys.platform.startswith("linux"):
        # Without a desktop keyring Chrome blocks on D-Bus the first time it touches the cookie store.
        cmd += ["--password-store=basic", "--use-mock-keychain"]
    if headless:
        cmd.append("--headless=new")
    if proxy:
        cmd.append(f"--proxy-server={proxy}")
    if os.geteuid() == 0:
        cmd.append("--no-sandbox")  # Chrome refuses to run as root otherwise (containers)
    return cmd


def cdp_version(timeout: float = 1.5) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(browser.cdp_url().rstrip("/") + "/json/version", timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _read_pids() -> dict[str, int]:
    try:
        return json.loads(pid_file().read_text())
    except (OSError, ValueError):
        return {}


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start(headless: bool = False, proxy: str | None = None, timeout: float = 30.0, tz: str | None = None) -> dict[str, Any]:
    """Idempotent: if CDP answers, return `already_running`."""
    if cdp_version():
        return {"state": "already_running", "cdp_url": browser.cdp_url(), "pid": _read_pids().get("chrome")}
    proxy = proxy or os.getenv("FINSOCNET_PROXY") or None
    browser.profile_dir().mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    pids: dict[str, int] = {}
    if tz:
        env["TZ"] = tz
    if not headless and not env.get("DISPLAY"):
        display = os.getenv("XVFB_DISPLAY", ":99")
        if not shutil.which("Xvfb"):
            raise CliError("UNSUPPORTED", "no DISPLAY and Xvfb is not installed", "install xvfb, or start with --headless for debugging")
        xvfb = subprocess.Popen(["Xvfb", display, "-screen", "0", "1366x900x24", "-nolisten", "tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        pids["xvfb"] = xvfb.pid
        env["DISPLAY"] = display
        time.sleep(0.7)
    cmd = build_command(find_chrome(), headless, proxy)
    assert not any(f in " ".join(cmd) for f in FORBIDDEN_FLAGS)
    log = open(browser.profile_dir() / ".chrome.log", "ab")
    proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=log, start_new_session=True)
    pids["chrome"] = proc.pid
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cdp_version():
            break
        if proc.poll() is not None:
            raise CliError("BROWSER_UNAVAILABLE", f"Chrome exited with code {proc.returncode}", f"see {browser.profile_dir() / '.chrome.log'}")
        time.sleep(0.4)
    else:
        proc.terminate()
        raise CliError("BROWSER_UNAVAILABLE", "Chrome did not open the CDP port in time", f"see {browser.profile_dir() / '.chrome.log'}")
    pid_file().write_text(json.dumps(pids))
    pid_file().chmod(0o600)
    return {"state": "started", "cdp_url": browser.cdp_url(), "pids": pids, "headless": headless, "proxy": proxy, "display": env.get("DISPLAY")}


def stop() -> dict[str, Any]:
    pids = _read_pids()
    stopped = []
    for name in ("chrome", "xvfb"):
        pid = pids.get(name)
        if _alive(pid):
            os.killpg(pid, signal.SIGTERM) if name == "chrome" else os.kill(pid, signal.SIGTERM)
            stopped.append(name)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and any(_alive(pids.get(n)) for n in ("chrome", "xvfb")):
        time.sleep(0.2)
    pid_file().unlink(missing_ok=True)
    return {"stopped": stopped, "cdp_reachable": bool(cdp_version())}


def status(with_ip: bool = False) -> dict[str, Any]:
    pids = _read_pids()
    ver = cdp_version()
    out: dict[str, Any] = {"pid": pids.get("chrome"), "process_alive": _alive(pids.get("chrome")), "cdp_url": browser.cdp_url(), "cdp_reachable": bool(ver),
                           "version": (ver or {}).get("Browser"), "proxy": os.getenv("FINSOCNET_PROXY") or None, "profile_dir": str(browser.profile_dir())}
    if ver:
        try:
            pw, b, ctx = browser.attach()
            try:
                out["open_pages"] = len(ctx.pages)
                if with_ip:
                    pg = ctx.new_page()
                    try:
                        pg.goto("https://api.ipify.org", timeout=10000)
                        out["egress_ip"] = pg.inner_text("body").strip()[:64]
                    except Exception as e:  # noqa: BLE001
                        out["egress_ip"] = None
                        out["egress_error"] = "proxy unreachable" if out["proxy"] else type(e).__name__
                    finally:
                        pg.close()
            finally:
                pw.stop()
        except CliError:
            pass
    return out

"""Login probes (docs/spec/04 §4.3): `logged_in` needs the session cookies AND a probe page that is neither a login wall
nor a checkpoint."""

from __future__ import annotations

from typing import Any, Callable

from finsocnet.core import browser

Fetch = Callable[[str], tuple[str, str]]  # url -> (final_url, visible text or body)


def session_present(platform: str, cookie_names_by_domain: dict[str, set[str]], local_storage_keys: set[str]) -> bool:
    cfg = browser.platforms().get(platform, {})
    names: set[str] = set()
    for dom, ns in cookie_names_by_domain.items():
        names |= ns
    needed = cfg.get("session_cookies")
    if needed and not set(needed) <= names:
        return False
    keys = cfg.get("local_storage_keys")
    if keys and not set(keys) <= local_storage_keys:
        return False
    return bool(needed or keys) or bool(names or local_storage_keys)


def probe(platform: str, fetch: Fetch) -> str:
    cfg = browser.platforms().get(platform, {})
    url = cfg.get("probe_url")
    if not url:
        return "unknown"
    final_url, text = fetch(url)
    hit = browser.classify_page(platform, final_url, text)
    if hit:
        return "checkpoint" if hit[0] == "CHECKPOINT" else "logged_out"
    path = cfg.get("logged_in_json_path")
    if path:
        import json
        try:
            node: Any = json.loads(text)
            for key in path.split("."):
                node = node[key]
            return "logged_in" if node else "logged_out"
        except (ValueError, KeyError, TypeError):
            return "logged_out"
    return "logged_in"


def login_state(platform: str, cookie_names_by_domain: dict[str, set[str]], local_storage_keys: set[str], fetch: Fetch | None) -> str:
    if not session_present(platform, cookie_names_by_domain, local_storage_keys):
        return "logged_out"
    if fetch is None:
        return "unknown"
    return probe(platform, fetch)

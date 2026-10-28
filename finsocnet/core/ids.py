"""Identifier builders and parsers (specs/00-conventions.md §4). Never hand-format IDs."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from secrets import token_hex
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PLATFORMS = (
    "youtube podcast x reddit medium substack web google file book arxiv paper discord telegram stackexchange "
    "forum tradingview facebook rss sec github bluesky stocktwits tiktok instagram threads linkedin seekingalpha "
    "hackernews"
).split()

def custom_platforms() -> list[str]:
    """Platforms added by `platform-skill-builder`: one recipe file `config/sites/<name>.yaml` each."""
    from finsocnet.core import config
    d = config.repo_root() / "config" / "sites"
    return sorted(p.stem for p in d.glob("*.yaml")) if d.is_dir() else []


def known_platforms() -> list[str]:
    return [*PLATFORMS, *[p for p in custom_platforms() if p not in PLATFORMS]]


_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|ref|ref_src)$")


def _check_platform(platform: str) -> str:
    p = platform.lower()
    if p not in PLATFORMS and p not in custom_platforms():
        raise ValueError(f"unknown platform {platform!r}")
    return p


def content_id(platform: str, *native: str) -> str:
    """`<platform>:<native_id>`; extra parts are joined with ':' (e.g. substack:example:139876543)."""
    return ":".join([_check_platform(platform), *[str(n) for n in native]])


def source_id(platform: str, kind: str, native: str) -> str:
    return f"{_check_platform(platform)}:{kind}:{native}"


def parse_id(value: str) -> tuple[str, str]:
    """Split `<platform>:<rest>` into (platform, rest)."""
    platform, sep, rest = value.partition(":")
    if not sep or not rest:
        raise ValueError(f"malformed id {value!r}")
    return platform, rest


def canonical_url(url: str, platform: str | None = None) -> str:
    """Lowercase scheme+host, drop fragment/tracking params/trailing slash (except root)."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    is_x = host.endswith("x.com") or host.endswith("twitter.com")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _TRACKING.match(k) and not (is_x and k == "s")
    ]
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), ""))


def web_content_id(url: str) -> str:
    return content_id("web", hashlib.sha1(canonical_url(url).encode()).hexdigest()[:16])


def file_content_id(sha256_hex: str) -> str:
    return content_id("file", sha256_hex[:16])


def rss_source_id(feed_url: str) -> str:
    return source_id("rss", "feed", hashlib.sha1(feed_url.encode()).hexdigest()[:12])


def slugify(text: str) -> str:
    """Lowercase ASCII slug."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "unknown"


def person_id(canonical_name: str, taken: set[str] | None = None) -> str:
    """Slug of the canonical name; collisions get -2, -3."""
    base = slugify(canonical_name)
    taken = taken or set()
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def handle_person_id(platform: str, handle: str) -> str:
    return f"{_check_platform(platform)}-{slugify(handle.lstrip('@'))}"


def bundle_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"b-{now.strftime('%Y%m%d%H%M%S')}-{token_hex(2)}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_since(value: str | None) -> str | None:
    """`7d`, `12h`, `2w` (relative to now) or an ISO date/time -> UTC ISO string comparable with stored timestamps."""
    if not value:
        return None
    m = re.fullmatch(r"(\d+)([hdw])", value.strip().lower())
    if not m:
        return value
    from datetime import timedelta
    delta = timedelta(**{{"h": "hours", "d": "days", "w": "weeks"}[m.group(2)]: int(m.group(1))})
    return (datetime.now(timezone.utc) - delta).strftime("%Y-%m-%dT%H:%M:%SZ")

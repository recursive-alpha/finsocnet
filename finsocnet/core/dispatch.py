"""Map a pasted URL/handle/query to (target_kind, platform, skill) with the rules of docs/spec/06 §1.3."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from finsocnet.core import config

# (regex on the full URL, platform key, skill, default action)
URL_RULES: list[tuple[str, str, str, str]] = [
    (r"(youtube\.com/(watch|shorts|live)|youtu\.be/)", "youtube", "youtube-extractor", "fetch"),
    (r"youtube\.com/(@|channel/|c/)", "youtube", "youtube-extractor", "profile"),
    (r"(x|twitter)\.com/[^/]+/status/", "x", "x-explorer", "fetch"),
    (r"(x|twitter)\.com/[^/?#]+/?$", "x", "x-explorer", "profile"),
    (r"reddit\.com/r/[^/]+/comments/", "reddit", "reddit-explorer", "fetch"),
    (r"reddit\.com/(r|user)/", "reddit", "reddit-explorer", "profile"),
    (r"medium\.com/.*-[0-9a-f]{10,12}(\?|$|/)", "medium", "medium-explorer", "fetch"),
    (r"medium\.com/", "medium", "medium-explorer", "list"),
    (r"([\w-]+\.)?substack\.com/p/|/p/[\w-]+$", "substack", "substack-explorer", "fetch"),
    (r"substack\.com", "substack", "substack-explorer", "list"),
    (r"(discord\.com/channels|discord\.gg)/", "discord", "discord-explorer", "fetch"),
    (r"t\.me/", "telegram", "telegram-explorer", "list"),
    (r"(stackexchange\.com|stackoverflow\.com)/(questions/tagged/|users/\d+)", "stackexchange", "stackexchange-explorer", "list"),
    (r"(stackexchange\.com|stackoverflow\.com)/(questions|q)/", "stackexchange", "stackexchange-explorer", "fetch"),
    (r"tradingview\.com/(chart|script)/", "tradingview", "tradingview-explorer", "fetch"),
    (r"tradingview\.com/u/", "tradingview", "tradingview-explorer", "profile"),
    (r"(facebook\.com|fb\.com)/", "facebook", "facebook-explorer", "fetch"),
    (r"sec\.gov/", "sec", "sec-edgar-explorer", "fetch"),
    (r"arxiv\.org/(abs|pdf)/", "arxiv", "paper-code-explorer", "fetch"),
    (r"(ssrn\.com|doi\.org|openalex\.org)/", "paper", "research-explorer", "fetch"),
    (r"github\.com/", "github", "github-explorer", "fetch"),
    (r"bsky\.app/profile/[^/]+/post/", "bluesky", "bluesky-explorer", "fetch"),
    (r"bsky\.app/profile/", "bluesky", "bluesky-explorer", "profile"),
    (r"(podcasts\.apple\.com|/feed/?$|\.rss$|feeds\.)", "podcast", "podcast-explorer", "list"),
    (r"stocktwits\.com/", "stocktwits", "stocktwits-explorer", "list"),
    (r"tiktok\.com/", "tiktok", "tiktok-explorer", "fetch"),
    (r"instagram\.com/", "instagram", "instagram-explorer", "fetch"),
    (r"threads\.(net|com)/", "threads", "threads-explorer", "fetch"),
    (r"linkedin\.com/", "linkedin", "linkedin-explorer", "fetch"),
    (r"seekingalpha\.com/", "seekingalpha", "seekingalpha-explorer", "fetch"),
    (r"news\.ycombinator\.com/item", "hackernews", "hackernews-explorer", "fetch"),
    (r"\.(pdf|epub|docx)(\?|$)", "file", "document-reader", "fetch"),
]


def forum_hosts() -> set[str]:
    try:
        import yaml
        p = config.repo_root() / "config" / "forums.yaml"
        return {f["host"] for f in (yaml.safe_load(p.read_text()) or {}).get("forums", [])} if p.exists() else set()
    except Exception:  # noqa: BLE001
        return set()


def classify(target: str, known_person_ids: set[str] | None = None) -> dict[str, str]:
    """`{target_kind, platform, skill, action}` for a user seed (url, @handle, person id or free-text query)."""
    t = target.strip()
    if re.match(r"^https?://", t):
        host = urlsplit(t).netloc.lower().removeprefix("www.")
        if host in forum_hosts():
            return {"target_kind": "url", "platform": "forum", "skill": "forum-explorer", "action": "fetch"}
        for rx, platform, skill, action in URL_RULES:
            if re.search(rx, t):
                return {"target_kind": "url", "platform": platform, "skill": skill, "action": action}
        return {"target_kind": "url", "platform": "web", "skill": "web-reader", "action": "fetch"}
    if known_person_ids and t in known_person_ids:
        return {"target_kind": "person", "platform": "", "skill": "source-explorer", "action": "profile"}
    if re.match(r"^@[\w.]{2,30}$", t):
        return {"target_kind": "handle", "platform": "", "skill": "source-explorer", "action": "profile"}
    if re.match(r"^(book|isbn):", t, re.I):
        return {"target_kind": "book", "platform": "book", "skill": "annas-archive-explorer", "action": "search"}
    return {"target_kind": "query", "platform": "", "skill": "web-searcher", "action": "search"}

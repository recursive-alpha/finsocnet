"""Substack JSON endpoints (docs/spec/05 §2.7). The endpoints are unofficial; behavior verified 2026-10-28:
`/api/v1/archive`, `/api/v1/posts/<slug>`, `/api/v1/post/<id>/comments` answer to plain HTTP for free posts. Publication
search answers an empty list without a browser session."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_paragraphs, html_to_markdown, refs


def pub_base(x: str) -> str:
    """Normalize a publication reference to its base URL: `name`, `name.substack.com`, or a custom domain URL."""
    x = x.strip()
    if x.startswith("substack:publication:"):
        x = x.split(":", 2)[2]
    if not x.startswith("http"):
        x = f"https://{x}.substack.com" if "." not in x else f"https://{x}"
    u = urlsplit(x)
    return f"{u.scheme}://{u.netloc}"


def subdomain(base: str, api: dict[str, Any] | None = None) -> str:
    host = urlsplit(base).netloc
    if host.endswith(".substack.com"):
        return host.split(".")[0]
    return (api or {}).get("subdomain") or host.replace(".", "-")


def split_post_ref(item: str) -> tuple[str, str]:
    m = re.match(r"(https?://[^/]+)/p/([\w-]+)", item.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a Substack post from {item!r}", "use https://<publication>/p/<slug>")
    return m.group(1), m.group(2)


def archive_refs(base: str, d: list[dict[str, Any]], sub: str) -> list[dict[str, Any]]:
    return [item_ref(p.get("canonical_url") or f"{base}/p/{p['slug']}", f"substack:{sub}:{p['id']}", "article", p.get("title"),
                     ((p.get("publishedBylines") or [{}])[0]).get("name"), p.get("post_date"), p.get("subtitle") or p.get("description"),
                     {"reactions": sum((p.get("reactions") or {}).values()) if isinstance(p.get("reactions"), dict) else None, "audience": p.get("audience")}) for p in d]


def comment_segments(comments: list[dict[str, Any]], start_seq: int) -> list[dict[str, Any]]:
    segs = []
    for c in comments:
        if c.get("deleted") or not c.get("body"):
            continue
        segs.append({"seq": start_seq + len(segs), "kind": "comment", "locator": {"comment_id": str(c["id"]), "parent_id": (c.get("ancestor_path") or "").split(".")[-1] or None},
                     "author": {"handle": c.get("handle") or c.get("name"), "display_name": c.get("name"), "platform_user_id": str(c.get("user_id") or "") or None}, "text": c["body"].strip()})
    return segs


def build_record(base: str, sub: str, p: dict[str, Any], comments: list[dict[str, Any]], raw_path: str | None) -> dict[str, Any]:
    body = p.get("body_html") or ""
    segs = html_paragraphs(body)
    truncated = p.get("audience") in ("only_paid", "founding") and len(re.sub(r"<[^>]+>", "", body)) < 1500
    if not segs:
        segs = [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": p.get("subtitle") or p.get("title") or "(no body)"}]
    segs += comment_segments(comments, len(segs))
    r = refs(html_to_markdown(body) + " " + " ".join(re.findall(r'href="([^"]+)"', body)))
    bylines = p.get("publishedBylines") or [{}]
    ctype = "episode" if p.get("type") == "podcast" or p.get("podcast_url") else "article"
    return content_record(f"substack:{sub}:{p['id']}", "substack", ctype, segs, url=p.get("canonical_url") or f"{base}/p/{p['slug']}", title=p.get("title"), description=p.get("subtitle"),
                          author={"handle": bylines[0].get("handle") or bylines[0].get("name"), "display_name": bylines[0].get("name"), "platform_user_id": str(bylines[0].get("id") or "") or None},
                          published_at=p.get("post_date"), language="en", metrics={"reactions": sum((p.get("reactions") or {}).values()) if isinstance(p.get("reactions"), dict) else None, "comments": len(comments)},
                          links=r["links"], mentions=r["mentions"], media=[{"kind": "audio", "url": p["podcast_url"]}] if p.get("podcast_url") else [], raw_path=raw_path, fetch_method="api",
                          extra={"audience": p.get("audience"), "truncated": truncated, "needs_audio": ctype == "episode" and len(body) < 200, "slug": p.get("slug"), "subtitle": p.get("subtitle")},
                          source={"id": f"substack:publication:{sub}", "kind": "publication", "title": sub, "url": base})


class Substack(PlatformAdapter):
    platform = "substack"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"fetch": [(("--no-comments",), {"action": "store_true"})]}

    def search(self, query, *, limit=20, since=None, **_):
        d = http.get_json("https://substack.com/api/v1/publication/search", platform="substack", params={"query": query, "page": 0, "limit": min(limit, 50)})
        out = [item_ref(f"https://{r.get('subdomain')}.substack.com", f"substack:publication:{r.get('subdomain')}", "publication", r.get("name"), r.get("author_name"), None, r.get("hero_text"))
               for r in d.get("results", [])]
        if not out:
            raise CliError("UNSUPPORTED", "Substack search returned nothing without a session", "use google-searcher/web-searcher with `site:substack.com <query>`, then `list` the publication")
        return out[:limit]

    def profile(self, target, **_):
        base = pub_base(target)
        d = http.get_json(f"{base}/api/v1/archive", platform="substack", params={"sort": "new", "limit": 1})
        sub = subdomain(base, {})
        by = ((d[0].get("publishedBylines") or [{}])[0]) if d else {}
        return profile_record("substack", f"substack:publication:{sub}", sub, display_name=by.get("name") or sub, bio=by.get("bio"), avatar_url=by.get("photo_url"), profile_url=base, links=[base])

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        base = pub_base(source)
        sub = subdomain(base)
        d = http.get_json(f"{base}/api/v1/archive", platform="substack", params={"sort": "new", "offset": int(cursor or 0), "limit": min(limit, 50)})
        items = [i for i in archive_refs(base, d, sub) if not since or (i["published_at"] or "")[:10] >= since]
        return list_result(items[:limit], str(int(cursor or 0) + len(d)) if len(d) >= min(limit, 50) else None, {"id": f"substack:publication:{sub}"})

    def fetch(self, item, *, no_comments=False, **_):
        base, slug = split_post_ref(item)
        sub = subdomain(base)
        p = http.get_json(f"{base}/api/v1/posts/{slug}", platform="substack")
        comments: list[dict[str, Any]] = []
        if not no_comments:
            try:
                comments = http.get_json(f"{base}/api/v1/post/{p['id']}/comments", platform="substack", params={"all_comments": "true", "sort": "best_first"}).get("comments", [])
            except CliError:
                comments = []
        return build_record(base, sub, p, comments, save_raw("substack", f"{sub}_{p['id']}", {"post": p, "comments": comments}))

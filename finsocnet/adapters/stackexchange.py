"""Stack Exchange API 2.3 (docs/spec/05 §3.3). Honours `backoff` and stops below 10 quota."""

from __future__ import annotations

import html
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_to_markdown, refs

API = "https://api.stackexchange.com/2.3"
SITES = {"quant", "money", "stackoverflow", "economics", "stats", "datascience"}
CODE_RE = re.compile(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", re.S)


def iso(ts: int | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def parse_ref(item: str, default_site: str) -> tuple[str, str]:
    """`https://quant.stackexchange.com/questions/123/slug`, `stackexchange:quant:123` or `123` -> (site, question id)."""
    m = re.search(r"https?://(?:([a-z]+)\.stackexchange\.com|(stackoverflow)\.com)/(?:questions|q)/(\d+)", item)
    if m:
        return (m.group(1) or m.group(2)), m.group(3)
    m = re.fullmatch(r"stackexchange:([a-z]+):(\d+)", item)
    if m:
        return m.group(1), m.group(2)
    if item.isdigit():
        return default_site, item
    raise CliError("USAGE", f"cannot read a question from {item!r}", "give a question URL, stackexchange:<site>:<id>, or an id with --site")


def body_segments(body_html: str, base_locator: dict[str, Any], kind: str, start_seq: int, author: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Text paragraphs become one segment (markdown); fenced code blocks become separate `code` segments."""
    segs: list[dict[str, Any]] = []
    blocks = [html.unescape(re.sub(r"<[^>]+>", "", b)) for b in CODE_RE.findall(body_html or "")]
    text = html_to_markdown(CODE_RE.sub(" ", body_html or ""))
    if text.strip():
        segs.append({"seq": start_seq, "kind": kind, "locator": dict(base_locator), "text": text})
    for i, code in enumerate(blocks):
        if code.strip():
            segs.append({"seq": start_seq + len(segs), "kind": "code", "locator": {**base_locator, "block": i}, "text": code.strip("\n")})
    if author:
        for sg in segs:
            sg["author"] = author
    return segs


def build_record(site: str, question: dict[str, Any], answers: list[dict[str, Any]], comments: list[dict[str, Any]] | None, raw_path: str | None) -> dict[str, Any]:
    qid = question["question_id"]
    q_owner = question.get("owner") or {}
    segs = body_segments(f"<h1>{html.escape(question.get('title', ''))}</h1>" + question.get("body", ""), {"post_id": qid}, "question", 0,
                         {"handle": q_owner.get("display_name"), "platform_user_id": str(q_owner.get("user_id") or "") or None})
    for a in answers:
        o = a.get("owner") or {}
        segs += body_segments(a.get("body", ""), {"post_id": a["answer_id"], "score": a.get("score"), "accepted": bool(a.get("is_accepted"))}, "answer", len(segs),
                              {"handle": o.get("display_name"), "platform_user_id": str(o.get("user_id") or "") or None})
    for c in comments or []:
        txt = html_to_markdown(c.get("body", ""))
        if txt:
            segs.append({"seq": len(segs), "kind": "comment", "locator": {"comment_id": c["comment_id"], "parent_id": c.get("post_id"), "score": c.get("score")},
                         "author": {"handle": (c.get("owner") or {}).get("display_name")}, "text": txt})
    owner = question.get("owner") or {}
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(
        f"stackexchange:{site}:{qid}", "stackexchange", "question", segs, url=question.get("link"), title=html.unescape(question.get("title", "")),
        author={"handle": owner.get("display_name"), "platform_user_id": str(owner.get("user_id") or "") or None, "profile_url": owner.get("link")},
        published_at=iso(question.get("creation_date")), language="en", metrics={"score": question.get("score"), "views": question.get("view_count"), "answers": question.get("answer_count")},
        links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="api",
        extra={"tags": question.get("tags", []), "site": site, "accepted_answer_id": question.get("accepted_answer_id")},
        source={"id": f"stackexchange:site:{site}", "kind": "site", "title": f"Stack Exchange: {site}"})


class StackExchange(PlatformAdapter):
    platform = "stackexchange"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {
        "search": [(("--site",), {"default": "quant"}), (("--tagged",), {}), (("--accepted",), {"action": "store_true"})],
        "profile": [(("--site",), {"default": "quant"})],
        "list": [(("--site",), {"default": "quant"}), (("--kind",), {"default": "questions", "choices": ["questions", "answers"]})],
        "fetch": [(("--site",), {"default": "quant"}), (("--comments",), {"action": "store_true"})],
    }

    def _get(self, path: str, site: str, **params: Any) -> dict[str, Any]:
        p = {"site": site, **params}
        if os.getenv("STACKEXCHANGE_KEY"):
            p["key"] = os.environ["STACKEXCHANGE_KEY"]
        data = http.get_json(f"{API}{path}", platform="stackexchange", params=p)
        if data.get("backoff"):
            time.sleep(min(int(data["backoff"]), 30))
        if data.get("quota_remaining", 999) < 10:
            raise CliError("RATE_LIMITED", "Stack Exchange quota almost used up", "set STACKEXCHANGE_KEY or wait until tomorrow", retry_after_sec=3600)
        return data

    def search(self, query, *, limit=20, since=None, site="quant", tagged=None, accepted=False, **_):
        params: dict[str, Any] = {"q": query, "sort": "votes", "order": "desc", "pagesize": min(limit, 100), "filter": "withbody"}
        if tagged:
            params["tagged"] = tagged
        if accepted:
            params["accepted"] = "True"
        if since:
            params["fromdate"] = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())
        d = self._get("/search/advanced", site, **params)
        return [item_ref(q["link"], f"stackexchange:{site}:{q['question_id']}", "question", html.unescape(q["title"]), (q.get("owner") or {}).get("display_name"), iso(q.get("creation_date")),
                         html_to_markdown(q.get("body", ""))[:300], {"score": q.get("score"), "answers": q.get("answer_count")}) for q in d.get("items", [])][:limit]

    def profile(self, target, *, site="quant", **_):
        uid = re.search(r"(\d+)", target).group(1)  # type: ignore[union-attr]
        u = self._get(f"/users/{uid}", site)["items"][0]
        return profile_record("stackexchange", f"stackexchange:user:{site}:{uid}", u.get("display_name", uid), display_name=u.get("display_name"), bio=html_to_markdown(u.get("about_me") or "") or None,
                              followers=None, verified=None, avatar_url=u.get("profile_image"), profile_url=u.get("link"), location=u.get("location"),
                              joined_at=iso(u.get("creation_date")), links=[u["website_url"]] if u.get("website_url") else [])

    def list(self, source, *, limit=50, cursor=None, since=None, site="quant", kind="questions", **_):
        m = re.search(r"https?://(?:([a-z]+)\.stackexchange\.com|(stackoverflow)\.com)/(?:questions/tagged/([^/?#]+)|users/(\d+))", source)
        if m:  # a tag or user page URL, as the explore queue stores it
            site, source = (m.group(1) or m.group(2)), (m.group(3) or m.group(4))
        if source.isdigit():
            path, src = f"/users/{source}/{kind}", f"stackexchange:user:{site}:{source}"
        else:
            path, src = "/questions", f"stackexchange:tag:{site}:{source}"
        params: dict[str, Any] = {"sort": "votes", "order": "desc", "pagesize": min(limit, 100), "page": int(cursor or 1), "filter": "withbody"}
        if not source.isdigit():
            params["tagged"] = source
        d = self._get(path, site, **params)
        items = [item_ref(q.get("link", ""), f"stackexchange:{site}:{q.get('question_id')}", "question", html.unescape(q.get("title", "")), (q.get("owner") or {}).get("display_name"),
                          iso(q.get("creation_date")), None, {"score": q.get("score")}) for q in d.get("items", [])]
        return list_result(items, str(int(cursor or 1) + 1) if d.get("has_more") else None, {"id": src})

    def fetch(self, item, *, site="quant", comments=False, **_):
        site, qid = parse_ref(item, site)
        q = self._get(f"/questions/{qid}", site, filter="withbody")
        if not q.get("items"):
            raise CliError("NOT_FOUND", f"question {qid} not found on {site}")
        a = self._get(f"/questions/{qid}/answers", site, filter="withbody", sort="votes", pagesize=100)
        cm = None
        if comments:
            ids = ";".join([qid] + [str(x["answer_id"]) for x in a.get("items", [])])
            cm = self._get(f"/posts/{ids}/comments", site, filter="withbody", pagesize=100).get("items", [])
        raw = save_raw("stackexchange", f"{site}_{qid}", {"question": q, "answers": a, "comments": cm})
        return build_record(site, q["items"][0], a.get("items", []), cm, raw)

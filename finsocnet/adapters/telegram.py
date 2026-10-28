"""Telegram public channels via the `t.me/s/<channel>` preview (specs/05 §3.2). Browser mode for private chats needs
the Telegram Web session and is a documented extension point (the preview is a static page, no login)."""

from __future__ import annotations

import re
from typing import Any

from lxml import html as lhtml

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

BASE = "https://t.me/s"
MSG = "//div[contains(@class,'tgme_widget_message ') and @data-post]"


def channel_name(x: str) -> str:
    m = re.search(r"(?:t\.me/(?:s/)?|telegram:channel:|@)?([A-Za-z0-9_]{4,})/?(?:\d+)?$", x.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a Telegram channel from {x!r}")
    return m.group(1)


def _text(el: Any) -> str:
    for br in el.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    return "".join(el.itertext()).strip()


def parse_channel(page: str) -> dict[str, Any]:
    root = lhtml.fromstring(page)
    info = {
        "title": " ".join("".join(root.xpath("//div[contains(@class,'tgme_channel_info_header_title')]//text()")).split()),
        "description": " ".join("".join(root.xpath("//div[contains(@class,'tgme_channel_info_description')]//text()")).split()) or None,
        "counters": {" ".join(c.xpath(".//*[contains(@class,'counter_type')]/text()")).strip(): " ".join(c.xpath(".//*[contains(@class,'counter_value')]/text()")).strip()
                     for c in root.xpath("//div[contains(@class,'tgme_channel_info_counter')]")},
        "more": (root.xpath("//a[contains(@class,'tme_messages_more')]/@href") or [None])[0],
    }
    msgs = []
    for m in root.xpath(MSG):
        post = m.get("data-post")
        txt_el = m.xpath(".//div[contains(@class,'tgme_widget_message_text')]")
        fwd = m.xpath(".//a[contains(@class,'tgme_widget_message_forwarded_from_name')]")
        media = [{"kind": "image", "url": re.search(r"url\('([^']+)'\)", s).group(1)} for s in m.xpath(".//a[contains(@class,'tgme_widget_message_photo_wrap')]/@style") if re.search(r"url\('([^']+)'\)", s)]
        msgs.append({"post": post, "channel": post.split("/")[0], "id": int(post.split("/")[1]), "text": _text(txt_el[0]) if txt_el else "", "date": (m.xpath(".//time/@datetime") or [None])[0],
                     "views": (m.xpath(".//span[contains(@class,'tgme_widget_message_views')]/text()") or [None])[0], "forwarded_from": _text(fwd[0]) if fwd else None, "media": media,
                     "links": [a for a in m.xpath(".//div[contains(@class,'tgme_widget_message_text')]//a/@href") if a.startswith("http")]})
    return {"info": info, "messages": msgs}


def msg_id(m: dict[str, Any]) -> str:
    return f"telegram:{m['channel']}:{m['id']}"


def message_ref(m: dict[str, Any]) -> dict[str, Any]:
    return item_ref(f"https://t.me/{m['post']}", msg_id(m), "post", None, m["channel"], m["date"], m["text"], {"views": m["views"]})


def message_record(m: dict[str, Any], channel_title: str | None, raw_path: str | None) -> dict[str, Any]:
    text = m["text"] or ("(media only)" if m["media"] else "(empty post)")
    r = refs(text)
    return content_record(msg_id(m), "telegram", "post", [{"seq": 0, "kind": "post", "locator": {"msg_id": m["id"]}, "author": {"handle": m["channel"]}, "text": text}], url=f"https://t.me/{m['post']}",
                          title=text[:80], author={"handle": m["channel"]}, published_at=m["date"], metrics={"views": m["views"]}, links=list(dict.fromkeys(r["links"] + m["links"])), mentions=r["mentions"],
                          media=m["media"], raw_path=raw_path, fetch_method="t.me/s", extra={"forwarded_from": m["forwarded_from"]},
                          source={"id": f"telegram:channel:{m['channel'].lower()}", "kind": "channel", "title": channel_title, "url": f"https://t.me/{m['channel']}"})


class Telegram(PlatformAdapter):
    platform = "telegram"
    capabilities = frozenset({"search", "profile", "list", "fetch"})

    def _page(self, ch: str, **params: Any) -> dict[str, Any]:
        txt = http.get_text(f"{BASE}/{ch}", platform="telegram", params=params or None)
        if "tgme_widget_message" not in txt and "tgme_channel_info" not in txt:
            raise CliError("NOT_FOUND", f"{ch} has no public preview (private channel or group)", "private chats need the browser mode with an imported Telegram Web session")
        save_raw("telegram", f"{ch}_{params.get('before', 'latest')}", txt, "html")
        return parse_channel(txt)

    def search(self, query, *, limit=20, since=None, channel=None, **_):
        if not channel:
            raise CliError("USAGE", "telegram search needs a channel: --channel NAME", "to discover channels use web-searcher with `--site t.me`")
        p = self._page(channel_name(channel), q=query)
        return [message_ref(m) for m in p["messages"]][:limit]

    def profile(self, target, **_):
        ch = channel_name(target)
        p = self._page(ch)
        i = p["info"]
        subs = i["counters"].get("subscribers")
        return profile_record("telegram", f"telegram:channel:{ch.lower()}", ch, display_name=i["title"], bio=i["description"], followers=subs, profile_url=f"https://t.me/{ch}",
                              links=refs(i["description"] or "")["links"])

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        ch = channel_name(source)
        items: list[dict[str, Any]] = []
        before = cursor
        nxt = None
        for _ in range(50):
            p = self._page(ch, **({"before": before} if before else {}))
            msgs = sorted(p["messages"], key=lambda m: -m["id"])
            for m in msgs:
                if since and (m["date"] or "")[:10] < since:
                    return list_result(items[:limit], None, {"id": f"telegram:channel:{ch.lower()}"})
                items.append(message_ref(m))
            more = p["info"]["more"]
            nxt = re.search(r"before=(\d+)", more).group(1) if more else None
            if len(items) >= limit or not nxt:
                break
            before = nxt
        return list_result(items[:limit], nxt if len(items) >= limit else None, {"id": f"telegram:channel:{ch.lower()}"})

    def fetch(self, item, **_):
        m = re.search(r"(?:t\.me/(?:s/)?|telegram:)?([A-Za-z0-9_]{4,})[/:](\d+)$", item.strip())
        if not m:
            raise CliError("USAGE", "give https://t.me/<channel>/<message_id>")
        ch, mid = m.group(1), int(m.group(2))
        p = self._page(ch, before=mid + 1)
        hit = next((x for x in p["messages"] if x["id"] == mid), None)
        if hit is None:
            raise CliError("NOT_FOUND", f"message {mid} is not in the public preview of {ch}")
        return message_record(hit, p["info"]["title"], None)

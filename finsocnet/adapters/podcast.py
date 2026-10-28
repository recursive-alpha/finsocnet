"""Podcasts: iTunes directory, RSS feeds, Podcasting 2.0 transcripts (docs/spec/05 §2.3)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import feedparser

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_paragraphs, refs, transcript_windows

ITUNES = "https://itunes.apple.com"
GUEST_RE = re.compile(r"(?:\bwith|\bft\.?|\bfeat\.?|\bfeaturing|\bw/)\s+([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,3})")
VTT_TIME = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})")


def feed_key(feed_url: str) -> str:
    return hashlib.sha1(feed_url.encode()).hexdigest()[:12]


def episode_id(feed_url: str, guid: str) -> str:
    return f"podcast:{feed_key(feed_url)}:{hashlib.sha1(guid.encode()).hexdigest()[:12]}"


def guests_hint(title: str, description: str = "") -> list[str]:
    return list(dict.fromkeys(m.strip(" .") for m in GUEST_RE.findall(f"{title}\n{description[:500]}")))


def parse_vtt_srt(text: str) -> list[dict[str, Any]]:
    entries, cur_t, buf = [], None, []
    for line in text.splitlines() + [""]:
        m = VTT_TIME.search(line)
        if m:
            g = m.groups()
            cur_t = (int(g[0] or 0) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000, int(g[4] or 0) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000)
            buf = []
        elif not line.strip():
            if cur_t and buf:
                entries.append({"start": cur_t[0], "end": cur_t[1], "text": " ".join(buf)})
            cur_t, buf = None, []
        elif cur_t and not line.strip().isdigit():
            buf.append(re.sub(r"<[^>]+>", "", line.strip()))
    return entries


def parse_json_transcript(text: str) -> list[dict[str, Any]]:
    d = json.loads(text)
    segs = d.get("segments", d if isinstance(d, list) else [])
    return [{"start": s.get("startTime", s.get("start", 0)), "end": s.get("endTime", s.get("end", 0)), "text": s.get("body", s.get("text", ""))} for s in segs]


def episode_record(feed_url: str, feed: Any, entry: Any, transcript: list[dict[str, Any]] | None, raw_path: str | None) -> dict[str, Any]:
    guid = entry.get("id") or entry.get("link") or entry.get("title")
    desc_html = entry.get("summary") or entry.get("description") or ""
    desc = re.sub(r"<[^>]+>", " ", desc_html)
    segs = transcript_windows(transcript) if transcript else (html_paragraphs(desc_html) if desc.strip() else [])
    enclosure = next((l.href for l in entry.get("links", []) if l.get("rel") == "enclosure"), None)
    r = refs(desc + " " + " ".join(re.findall(r'href="([^"]+)"', desc_html)))
    dur = entry.get("itunes_duration")
    seconds = None
    if dur:
        parts = [int(x) for x in str(dur).split(":") if x.isdigit()]
        seconds = sum(p * 60 ** i for i, p in enumerate(reversed(parts))) if parts else None
    published = None
    if entry.get("published_parsed"):
        from datetime import datetime, timezone
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return content_record(
        episode_id(feed_url, guid), "podcast", "episode", segs, url=entry.get("link"), title=entry.get("title"), description=desc.strip()[:2000] or None,
        author={"handle": feed.feed.get("author")}, published_at=published, duration_sec=seconds, links=r["links"], mentions=r["mentions"],
        media=[{"kind": "audio", "url": enclosure}] if enclosure else [], raw_path=raw_path, fetch_method="rss_transcript" if transcript else "rss_notes",
        extra={"show": feed.feed.get("title"), "guests_hint": guests_hint(entry.get("title", ""), desc), "has_transcript": bool(transcript), "needs_audio": not transcript, "enclosure": enclosure, "feed_url": feed_url},
        source={"id": f"podcast:feed:{feed_key(feed_url)}", "kind": "feed", "title": feed.feed.get("title"), "url": feed_url})


class Podcast(PlatformAdapter):
    platform = "podcast"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--episodes",), {"action": "store_true"})], "fetch": [(("--feed",), {"required": False})]}

    def search(self, query, *, limit=20, since=None, episodes=False, **_):
        d = http.get_json(f"{ITUNES}/search", platform="podcast", params={"media": "podcast", "entity": "podcastEpisode" if episodes else "podcast", "term": query, "limit": min(limit, 50)})
        out = []
        for r in d.get("results", []):
            if episodes:
                out.append(item_ref(r.get("trackViewUrl", ""), episode_id(r.get("feedUrl", r.get("collectionViewUrl", "")), r.get("episodeGuid", str(r.get("trackId")))), "episode",
                                    r.get("trackName"), r.get("collectionName"), r.get("releaseDate"), r.get("description"), {"duration_ms": r.get("trackTimeMillis")}))
            elif r.get("feedUrl"):
                out.append(item_ref(r["feedUrl"], f"podcast:feed:{feed_key(r['feedUrl'])}", "show", r.get("collectionName"), r.get("artistName"), r.get("releaseDate"), r.get("primaryGenreName"), {"episodes": r.get("trackCount")}))
        return out[:limit]

    def profile(self, target, **_):
        f = feedparser.parse(http.get_text(target, platform="podcast"))
        return profile_record("podcast", f"podcast:feed:{feed_key(target)}", target, display_name=f.feed.get("title"), bio=re.sub(r"<[^>]+>", " ", f.feed.get("subtitle") or f.feed.get("summary") or "").strip() or None,
                              avatar_url=(f.feed.get("image") or {}).get("href"), profile_url=f.feed.get("link") or target,
                              links=[f.feed["link"]] if f.feed.get("link") else [])

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        xml = http.get_text(source, platform="podcast")
        f = feedparser.parse(xml)
        out = []
        for e in f.entries:
            guid = e.get("id") or e.get("link")
            if cursor and guid == cursor:
                break
            ref = item_ref(f"{source}#{guid}", episode_id(source, guid), "episode", e.get("title"), f.feed.get("author"), e.get("published"), re.sub(r"<[^>]+>", " ", e.get("summary", ""))[:300])
            if not since or (e.get("published_parsed") and "%04d-%02d-%02d" % e.published_parsed[:3] >= since):
                out.append(ref)
        save_raw("podcast", feed_key(source), xml, "xml")
        return list_result(out[:limit], (f.entries[0].get("id") or f.entries[0].get("link")) if f.entries else None, {"id": f"podcast:feed:{feed_key(source)}", "title": f.feed.get("title")})

    def fetch(self, item, *, feed=None, **_):
        feed_url, guid = (item.split("#", 1) + [None])[:2] if "#" in item else (feed, item)
        if not feed_url:
            raise CliError("USAGE", "give <feed_url>#<guid> or an item with --feed")
        xml = http.get_text(feed_url, platform="podcast")
        f = feedparser.parse(xml)
        entry = next((e for e in f.entries if guid in (e.get("id"), e.get("link"), episode_id(feed_url, e.get("id") or e.get("link") or ""))), None)
        if entry is None:
            raise CliError("NOT_FOUND", f"episode {guid} is not in the feed")
        transcript = None
        for t in entry.get("podcast_transcript", []) if isinstance(entry.get("podcast_transcript"), list) else []:
            try:
                body = http.get_text(t["url"], platform="podcast")
                transcript = parse_json_transcript(body) if "json" in t.get("type", "") else parse_vtt_srt(body)
                if transcript:
                    break
            except (CliError, KeyError, ValueError):
                continue
        return episode_record(feed_url, f, entry, transcript, save_raw("podcast", guid or "episode", xml, "xml"))

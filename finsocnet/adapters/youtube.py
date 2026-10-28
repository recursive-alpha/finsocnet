"""YouTube via yt-dlp and youtube-transcript-api, Whisper fallback (specs/05 §2.1)."""

from __future__ import annotations

import re
from typing import Any

from finsocnet.core import config, transcribe
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw, since_ok
from finsocnet.core.segments import refs, transcript_windows

VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/|youtube:)([0-9A-Za-z_-]{11})(?![0-9A-Za-z_-])")
LONG_FORM_SEC = 3 * 3600


def video_id(ref: str) -> str:
    m = VIDEO_ID.search(ref.strip())
    if m:
        return m.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", ref.strip()):
        return ref.strip()
    raise CliError("USAGE", f"cannot read a YouTube video id from {ref!r}")


def upload_iso(d: str | None) -> str | None:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if d and re.fullmatch(r"\d{8}", d) else None


def content_type(info: dict[str, Any]) -> str:
    if info.get("was_live") or info.get("is_live") or info.get("live_status") in ("was_live", "is_live"):
        return "stream"
    if "/shorts/" in (info.get("webpage_url") or info.get("original_url") or "") or (info.get("duration") or 999) <= 60 and info.get("aspect_ratio", 2) < 1:
        return "short"
    return "video"


def choose_caption(options: list[tuple[str, bool]], original: str | None) -> int | None:
    """Pick among `(language_code, is_generated)`: manual original → manual en → auto original → auto en."""
    order = [(original, False), ("en", False), (original, True), ("en", True)]
    for lang, gen in order:
        if lang is None:
            continue
        for i, (l, g) in enumerate(options):
            if l.split("-")[0] == lang.split("-")[0] and g == gen:
                return i
    return None


def video_record(info: dict[str, Any], entries: list[dict[str, Any]] | None, caption_source: str | None, caption_lang: str | None, raw_path: str | None = None) -> dict[str, Any]:
    vid = info["id"]
    desc = info.get("description") or ""
    r = refs(desc)
    segs = transcript_windows(entries) if entries else []
    extra = {"caption_source": caption_source, "caption_lang": caption_lang, "chapters": [{"title": c.get("title"), "start_sec": c.get("start_time")} for c in info.get("chapters") or []],
             "long_form": (info.get("duration") or 0) > LONG_FORM_SEC, "tags": info.get("tags") or [], "caption_error": info.get("_caption_error")}
    cid = info.get("channel_id")
    return content_record(f"youtube:{vid}", "youtube", content_type(info), segs, url=info.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}", title=info.get("title"), description=desc,
                          author={"handle": info.get("uploader_id") or info.get("channel"), "display_name": info.get("channel") or info.get("uploader"), "platform_user_id": cid,
                                  "profile_url": info.get("channel_url")},
                          published_at=upload_iso(info.get("upload_date")), language=caption_lang or info.get("language"), duration_sec=int(info["duration"]) if info.get("duration") else None,
                          metrics={"views": info.get("view_count"), "likes": info.get("like_count"), "comments": info.get("comment_count")}, links=r["links"], mentions=r["mentions"],
                          media=[{"kind": "video", "url": f"https://www.youtube.com/watch?v={vid}"}], raw_path=raw_path, fetch_method="yt-dlp",
                          extra=extra, source={"id": f"youtube:channel:{cid}" if cid else f"youtube:handle:{(info.get('uploader_id') or 'unknown').lstrip('@').lower()}", "kind": "channel" if cid else "handle",
                                               "title": info.get("channel") or info.get("uploader"), "url": info.get("channel_url")})


def _ydl(extra: dict[str, Any] | None = None) -> Any:
    import yt_dlp
    opts: dict[str, Any] = {"quiet": True, "no_warnings": True, "skip_download": True, **(extra or {})}
    cookies = config.data_dir() / "sessions" / "cookies.txt"
    if cookies.exists():
        opts["cookiefile"] = str(cookies)
    return yt_dlp.YoutubeDL(opts)


def flat_ref(e: dict[str, Any]) -> dict[str, Any]:
    vid = e["id"]
    return item_ref(e.get("url") or f"https://www.youtube.com/watch?v={vid}", f"youtube:{vid}", "video", e.get("title"), e.get("channel") or e.get("uploader"), upload_iso(e.get("upload_date")),
                    e.get("description"), {"views": e.get("view_count"), "duration": e.get("duration")})


def channel_url(target: str) -> str:
    """A URL, a channel id (`UC` + 22 characters) or a handle (`@name` / `name`) -> the channel page URL."""
    if target.startswith("http"):
        return target
    return f"https://www.youtube.com/{'channel/' if re.fullmatch(r'UC[\w-]{22}', target) else '@'}{target.lstrip('@')}"


def channel_avatar(thumbs: list[dict[str, Any]]) -> str | None:
    """yt-dlp lists channel thumbnails: banners (wide) and `avatar_uncropped` (square). Prefer the square one."""
    sq = [t for t in thumbs if "avatar" in str(t.get("id", "")) and t.get("url")]
    if sq:
        return sq[0]["url"]
    sq = [t for t in thumbs if t.get("url") and t.get("width") and t.get("height") and t["width"] == t["height"]]
    return max(sq, key=lambda t: t["width"])["url"] if sq else None


class YouTube(PlatformAdapter):
    platform = "youtube"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--type",), {"default": "video", "choices": ["video", "channel"]})],
            "list": [(("--tab",), {"default": "videos", "choices": ["videos", "shorts", "streams", "all"]})],
            "fetch": [(("--no-whisper",), {"action": "store_true"}), (("--metadata-only",), {"action": "store_true"})]}

    def search(self, query, *, limit=20, since=None, type="video", **_):
        with _ydl({"extract_flat": True}) as y:
            r = y.extract_info(f"ytsearch{limit}:{query}", download=False)
        items = [flat_ref(e) for e in r.get("entries", []) if e.get("id")]
        if type == "channel":
            items = [i for i in items if i["author_handle"]]
        return [i for i in items if since_ok(i["published_at"], since)][:limit]

    def profile(self, target, **_):
        url = channel_url(target)
        with _ydl({"extract_flat": True, "playlistend": 1}) as y:
            r = y.extract_info(url.rstrip("/") + "/videos", download=False)
        cid = r.get("channel_id") or r.get("id")
        desc = r.get("description") or ""
        return profile_record("youtube", f"youtube:channel:{cid}", r.get("uploader_id") or target, display_name=r.get("channel") or r.get("title"), bio=desc or None,
                              followers=r.get("channel_follower_count"), profile_url=r.get("channel_url") or url, links=refs(desc)["links"], verified=None,
                              avatar_url=channel_avatar(r.get("thumbnails") or []))

    def list(self, source, *, limit=50, cursor=None, since=None, tab="videos", **_):
        base = channel_url(source)
        tabs = ["videos", "shorts", "streams"] if tab == "all" else [tab]
        items: list[dict[str, Any]] = []
        cid = None
        for t in tabs:
            try:
                with _ydl({"extract_flat": True, "playlistend": limit}) as y:
                    r = y.extract_info(f"{base.rstrip('/')}/{t}", download=False)
            except Exception:  # noqa: BLE001 - a channel may lack a tab
                continue
            cid = cid or r.get("channel_id")
            for e in r.get("entries", []):
                if e.get("id") == cursor:
                    break
                ref = flat_ref(e)
                ref["kind"] = {"shorts": "short", "streams": "stream"}.get(t, "video")
                items.append(ref)
        items = [i for i in items if since_ok(i["published_at"], since)][:limit]
        return list_result(items, items[0]["id"].split(":", 1)[1] if items else cursor, {"id": f"youtube:channel:{cid}" if cid else f"youtube:handle:{source.lstrip('@').lower()}"})

    def fetch(self, item, *, no_whisper=False, metadata_only=False, **_):
        vid = video_id(item)
        with _ydl() as y:
            info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        raw = save_raw("youtube", vid, info if isinstance(info, dict) else {})
        if metadata_only:
            return video_record(info, None, None, None, raw)
        entries, source, lang = self._captions(vid, info.get("language"))
        if not entries and getattr(self, "caption_error", None):
            info = {**info, "_caption_error": self.caption_error}
        if not entries and not no_whisper:
            res = transcribe.transcribe(f"https://www.youtube.com/watch?v={vid}", content_id=f"youtube:{vid}")
            entries, source, lang = transcribe.as_entries(res), "whisper", res.get("language")
        return video_record(info, entries, source, lang, raw)

    def _captions(self, vid: str, original: str | None) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
        from youtube_transcript_api import YouTubeTranscriptApi
        self.caption_error = None
        try:
            tl = list(YouTubeTranscriptApi().list(vid))
        except Exception as e:  # noqa: BLE001 - captions disabled, IP blocked, video private
            self.caption_error = type(e).__name__  # kept in extra.caption_error: a block (RequestBlocked, IpBlocked) is retryable, TranscriptsDisabled is not
            return None, None, None
        idx = choose_caption([(t.language_code, t.is_generated) for t in tl], original)
        if idx is None:
            return None, None, None
        t = tl[idx]
        try:
            fetched = t.fetch()
        except Exception as e:  # noqa: BLE001
            self.caption_error = type(e).__name__
            return None, None, None
        return [{"start": s.start, "duration": s.duration, "text": s.text} for s in fetched], "auto" if t.is_generated else "manual", t.language_code

"""Speech to text with local faster-whisper (the only model scripts run; ADR-002). Results are cached by audio hash."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from finsocnet.core import config
from finsocnet.core.output import CliError

AUDIO_EXT = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac", ".wma"}
VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".flv"}
_model_factory: Callable[[], Any] | None = None  # tests inject a fake model


def set_model_factory(f: Callable[[], Any] | None) -> None:
    global _model_factory
    _model_factory = f


def audio_dir() -> Path:
    return config.resolve_path(os.getenv("AUDIO_DOWNLOAD_DIR", "data/audio"))


def transcripts_dir() -> Path:
    return config.data_dir() / "transcripts"


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_url(x: str) -> bool:
    return bool(re.match(r"^https?://", x))


def download_audio(url: str) -> Path:
    """Any yt-dlp-supported URL (YouTube, Twitch VOD, Vimeo, Rumble, Kick, X video, TikTok, podcast enclosure)."""
    import yt_dlp
    audio_dir().mkdir(parents=True, exist_ok=True)
    cookies = config.data_dir() / "sessions" / "cookies.txt"
    opts: dict[str, Any] = {"format": "bestaudio/best", "outtmpl": str(audio_dir() / "%(extractor)s_%(id)s.%(ext)s"), "quiet": True, "no_warnings": True, "noprogress": True}
    if cookies.exists():
        opts["cookiefile"] = str(cookies)
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
        return Path(y.prepare_filename(info))


def load_model() -> Any:
    if _model_factory:
        return _model_factory()
    from faster_whisper import WhisperModel
    name = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3-turbo")
    device = os.getenv("WHISPER_DEVICE", "auto")
    compute = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    return WhisperModel(name.replace("openai/whisper-", "") if name.startswith("openai/whisper-") and "turbo" not in name else name, device=device, compute_type=compute)


def transcribe(source: str, language: str = "auto", content_id: str | None = None) -> dict[str, Any]:
    """Transcribe a local file or a URL. Returns `{segments:[{start_sec,end_sec,text}], language, model, duration_sec, cached, audio_sha256}`."""
    path = download_audio(source) if is_url(source) else Path(source).expanduser()
    if not path.exists():
        raise CliError("NOT_FOUND", f"{source} does not exist")
    digest = sha_file(path)
    cache = transcripts_dir() / f"{digest[:16]}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        data["cached"] = True
        return data
    model = load_model()
    segments, info = model.transcribe(str(path), language=None if language == "auto" else language, vad_filter=True, word_timestamps=False)
    out = [{"start_sec": round(float(s.start), 2), "end_sec": round(float(s.end), 2), "text": s.text.strip()} for s in segments if s.text.strip()]
    data = {"segments": out, "language": getattr(info, "language", None), "model": os.getenv("WHISPER_MODEL", "openai/whisper-large-v3-turbo"),
            "duration_sec": round(float(getattr(info, "duration", out[-1]["end_sec"] if out else 0)), 1), "audio_sha256": digest, "content_id": content_id, "cached": False}
    transcripts_dir().mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def as_entries(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"start": s["start_sec"], "end": s["end_sec"], "text": s["text"]} for s in result["segments"]]

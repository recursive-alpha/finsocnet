"""Download and store pictures (person avatars, source icons) as files under `data/media/` (specs/12-person-images.md).

Only raster images are accepted and they are identified by their bytes, not by the server's word: magic number, size limit, and Pillow
must be able to open them. Files are named by content hash, so the same picture is stored once.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from finsocnet.core import config, http
from finsocnet.core.output import CliError

MAX_BYTES = 8 * 1024 * 1024
MIN_BYTES = 200
_EXT = {"PNG": ("png", "image/png"), "JPEG": ("jpg", "image/jpeg"), "GIF": ("gif", "image/gif"), "WEBP": ("webp", "image/webp")}


def media_dir() -> Path:
    return config.data_dir() / "media"


def store_image_bytes(data: bytes, subdir: str, source: str = "") -> dict[str, Any]:
    """Validate `data` as an image and write it to `data/media/<subdir>/<sha256[:20]>.<ext>`. Returns the metadata row."""
    if not (MIN_BYTES <= len(data) <= MAX_BYTES):
        raise CliError("VALIDATION_ERROR", f"image {source or ''} has {len(data)} bytes (allowed {MIN_BYTES}..{MAX_BYTES})")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            fmt, (w, h) = im.format or "", im.size
    except Exception as e:  # noqa: BLE001 - Pillow raises many types for corrupt input
        raise CliError("VALIDATION_ERROR", f"{source or 'file'} is not a readable image: {type(e).__name__}") from e
    if fmt not in _EXT:
        raise CliError("VALIDATION_ERROR", f"unsupported image format {fmt!r} (png, jpeg, gif, webp)")
    ext, mime = _EXT[fmt]
    sha = hashlib.sha256(data).hexdigest()
    rel = Path("data") / "media" / subdir / f"{sha[:20]}.{ext}"
    dest = config.repo_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    return {"path": rel.as_posix(), "sha256": sha, "mime": mime, "width": w, "height": h, "bytes": len(data)}


def download_image(url: str, subdir: str, platform: str = "default") -> dict[str, Any]:
    """GET `url` (budgeted, retried, mapped to exit codes) and store it. Raises CliError."""
    if not url.startswith(("http://", "https://")):
        raise CliError("VALIDATION_ERROR", f"not an http(s) url: {url[:80]}")
    r = http.request("GET", url, platform=platform, headers={"Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8"}, retries=1)
    ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype and not ctype.startswith(("image/", "application/octet-stream", "binary/")):
        raise CliError("VALIDATION_ERROR", f"{url[:80]} answered {ctype}, not an image")
    return {**store_image_bytes(r.content, subdir, url), "source_url": url}


def read_file_image(path: str, subdir: str) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.is_file():
        raise CliError("NOT_FOUND", f"file {path} does not exist")
    return {**store_image_bytes(p.read_bytes(), subdir, path), "source_url": f"file://{p.name}"}

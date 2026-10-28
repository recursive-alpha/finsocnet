"""Documents: PDF, EPUB, DOCX, HTML, TXT/MD and audio/video recordings (specs/05 §2.11). Nothing is ignored: scanned
pages are OCRed when `ocrmypdf` is installed, recordings go through Whisper."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from finsocnet.core import config, http, transcribe
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record
from finsocnet.core.segments import html_to_markdown, paragraph_segments, refs, transcript_windows

TEXT_EXT = {".txt", ".md", ".markdown", ".rst", ".csv"}
HTML_EXT = {".html", ".htm", ".xhtml"}
BOOK_PAGES = 80
MIN_PAGE_CHARS = 50


def sha256_file(p: Path) -> str:
    return transcribe.sha_file(p)


def doc_id(path: Path, source_id: str | None) -> str:
    if source_id:
        return source_id
    return f"file:{sha256_file(path)[:16]}"


def pdf_segments(path: Path, ocr: str = "auto") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import pymupdf as fitz  # PyMuPDF
    doc = fitz.open(path)
    pages = [p.get_text("text") for p in doc]
    meta = {k: v for k, v in (doc.metadata or {}).items() if v}
    n_pages = len(pages)
    low = [i for i, t in enumerate(pages) if len(t.strip()) < MIN_PAGE_CHARS]
    ocred = 0
    if ocr != "off" and low and (ocr == "force" or shutil.which("ocrmypdf")):
        try:
            out = Path(tempfile.mkdtemp()) / "ocr.pdf"
            subprocess.run(["ocrmypdf", "--force-ocr" if ocr == "force" else "--skip-text", "--quiet", str(path), str(out)], check=True, capture_output=True, timeout=1800)
            pages2 = [p.get_text("text") for p in fitz.open(out)]
            ocred = sum(1 for i in low if len(pages2[i].strip()) >= MIN_PAGE_CHARS)
            pages = pages2
        except (subprocess.SubprocessError, OSError):
            pass
    segs = [{"seq": 0, "kind": "page", "locator": {"page": i + 1}, "text": t.strip()} for i, t in enumerate(pages) if t.strip()]
    meta.update({"pages": n_pages, "ocr_pages": ocred, "empty_pages": n_pages - len(segs)})
    return segs, meta


def epub_segments(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from ebooklib import ITEM_DOCUMENT, epub
    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    segs: list[dict[str, Any]] = []
    for ci, item in enumerate(i for i in book.get_items() if i.get_type() == ITEM_DOCUMENT):
        md = html_to_markdown(item.get_content().decode("utf-8", "replace"))
        title = (re.search(r"^#+\s*(.+)$", md, re.M) or [None, item.get_name()])[1].strip()
        for pi, p in enumerate(paragraph_segments(md, min_len=40)):
            segs.append({"seq": 0, "kind": "paragraph", "locator": {"chapter": title, "para": pi}, "text": p["text"]})
    md_ = {"title": (book.get_metadata("DC", "title") or [[None]])[0][0], "author": (book.get_metadata("DC", "creator") or [[None]])[0][0], "chapters": ci + 1 if segs else 0}
    return segs, {k: v for k, v in md_.items() if v}


def docx_segments(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import docx
    d = docx.Document(str(path))
    text = "\n\n".join(p.text for p in d.paragraphs if p.text.strip())
    for t in d.tables:
        text += "\n\n" + "\n".join(" | ".join(c.text.strip() for c in row.cells) for row in t.rows)
    props = d.core_properties
    return paragraph_segments(text, min_len=40), {k: v for k, v in {"title": props.title, "author": props.author}.items() if v}


def recording_segments(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    res = transcribe.transcribe(str(path))
    return transcript_windows(transcribe.as_entries(res)), {"language": res.get("language"), "duration_sec": res.get("duration_sec")}


def read_file(path: Path, ocr: str = "auto") -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """Return (segments, metadata, kind) for a file chosen by its content/extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        s, m = pdf_segments(path, ocr)
        return s, m, "pdf"
    if ext == ".epub":
        s, m = epub_segments(path)
        return s, m, "epub"
    if ext == ".docx":
        s, m = docx_segments(path)
        return s, m, "docx"
    if ext in HTML_EXT:
        return paragraph_segments(html_to_markdown(path.read_text("utf-8", "replace")), min_len=40), {}, "html"
    if ext in TEXT_EXT or not ext:
        return paragraph_segments(path.read_text("utf-8", "replace"), min_len=40), {}, "text"
    if ext in transcribe.AUDIO_EXT | transcribe.VIDEO_EXT:
        s, m = recording_segments(path)
        return s, m, "recording"
    raise CliError("UNSUPPORTED", f"cannot read {ext or 'files without extension'}", "supported: pdf epub docx html txt md and audio/video")


def build_record(path: Path, source_id: str | None = None, title: str | None = None, author: str | None = None, ocr: str = "auto", url: str | None = None) -> dict[str, Any]:
    segs, meta, kind = read_file(path, ocr)
    if not segs:
        segs = [{"seq": 0, "kind": "page", "locator": {"page": 1}, "text": f"(no extractable text in {path.name})"}]
    pages = meta.get("pages") or 0
    ctype = "recording" if kind == "recording" else "book" if (kind == "epub" or pages > BOOK_PAGES) else "paper" if kind == "pdf" and (source_id or "").startswith("arxiv:") else "file"
    cid = doc_id(path, source_id)
    platform = cid.split(":", 1)[0] if cid.split(":", 1)[0] in ("book", "arxiv", "file") else "file"
    r = refs("\n".join(s["text"] for s in segs[:200]))
    return content_record(cid, platform, ctype if ctype != "recording" else "file", segs, url=url, title=title or meta.get("title") or path.stem, author={"handle": author or meta.get("author")},
                          language=meta.get("language"), links=r["links"][:200], mentions=[], fetch_method=f"document:{kind}", extra={**meta, "file": path.name, "kind": kind, "sha256": sha256_file(path), "recording": kind == "recording"},
                          source={"id": f"file:site:local", "kind": "site", "title": "Local files"} if cid.startswith("file:") else None)


def download(url: str) -> Path:
    r = http.request("GET", url, platform="web", timeout=120)
    ext = Path(urlsplit(url).path).suffix or (".pdf" if "pdf" in r.headers.get("content-type", "") else ".html")
    d = config.data_dir() / "papers"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (hashlib.sha1(url.encode()).hexdigest()[:16] + ext)
    p.write_bytes(r.content)
    return p


class Document(PlatformAdapter):
    platform = "file"
    capabilities = frozenset({"fetch", "scan"})
    opts = {"fetch": [(("--title",), {}), (("--author",), {}), (("--source-id",), {}), (("--ocr",), {"default": "auto", "choices": ["auto", "force", "off"]})]}

    def fetch(self, item, *, title=None, author=None, source_id=None, ocr="auto", **_):
        url = item if item.startswith("http") else None
        path = download(item) if url else Path(item).expanduser()
        if not path.exists():
            raise CliError("NOT_FOUND", f"{item} does not exist")
        return build_record(path, source_id, title, author, ocr, url)

    def scan_dir(self, directory: str | None = None) -> list[tuple[Path, dict[str, Any] | None, str | None]]:
        d = Path(directory) if directory else config.data_dir() / "inbox" / "documents"
        d.mkdir(parents=True, exist_ok=True)
        out: list[tuple[Path, dict[str, Any] | None, str | None]] = []
        for p in sorted(x for x in d.iterdir() if x.is_file()):
            try:
                out.append((p, build_record(p), None))
            except CliError as e:
                out.append((p, None, e.message))
        return out

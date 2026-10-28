"""Anna's Archive through the agent browser (docs/spec/05 §2.12). DDoS-Guard clearance lives in the agent browser profile.
`download` runs only when called explicitly: downloading copyrighted books may be illegal in your jurisdiction."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlencode, urljoin

from lxml import html as lhtml

from finsocnet.adapters import _browser
from finsocnet.core import browser, config
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, save_raw

MD5 = re.compile(r"\b([a-f0-9]{32})\b")


def base_url() -> str:
    return os.getenv("ANNAS_ARCHIVE_URL", "https://annas-archive.gl").rstrip("/")


def md5_of(ref: str) -> str:
    m = MD5.search(ref.lower().replace("book:", ""))
    if not m:
        raise CliError("USAGE", f"cannot read a 32-character MD5 from {ref!r}")
    return m.group(1)


def parse_search(html: str, base: str) -> list[dict[str, Any]]:
    root = lhtml.fromstring(html)
    out, seen = [], set()
    for a in root.xpath("//a[contains(@href,'/md5/')]"):
        h = a.get("href", "")
        m = MD5.search(h)
        if not m or m.group(1) in seen:
            continue
        title = " ".join(("".join(a.xpath(".//h3//text()")) or "").split())
        if not title:
            continue
        seen.add(m.group(1))
        lines = [" ".join(t.split()) for t in a.itertext() if t.strip()]
        meta = next((l for l in lines if re.search(r"\b(pdf|epub|mobi|azw3|djvu|cbz)\b", l, re.I)), "")
        fmt = (re.search(r"\b(pdf|epub|mobi|azw3|djvu|cbz)\b", meta, re.I) or [None, None])[1]
        size = (re.search(r"([\d.]+\s?[KMG]B)", meta) or [None, None])[1]
        rest = [l for l in lines if l not in (title, meta)]
        out.append(item_ref(urljoin(base, h), f"book:{m.group(1)}", "book", title, rest[0] if rest else None, None, " | ".join(rest[1:3]) or None, {"format": fmt.lower() if fmt else None, "size": size}))
    return out


def parse_details(html: str, md5: str, base: str) -> dict[str, Any]:
    root = lhtml.fromstring(html)
    txt = lambda xp: " ".join(" ".join(root.xpath(xp)).split())
    title = txt("//div[contains(@class,'text-3xl')]//text()[1]") or txt("//h1//text()") or txt("//title/text()")
    desc = txt("//div[contains(@class,'js-md5-top-box-description')]//text()") or txt("//meta[@name='description']/@content")
    mirrors = []
    for a in root.xpath("//a[contains(@href,'slow_download') or contains(@href,'fast_download') or contains(@href,'libgen') or contains(@href,'ipfs')]"):
        mirrors.append({"label": " ".join(a.text_content().split())[:60], "url": urljoin(base, a.get("href"))})
    return {"md5": md5, "title": re.sub(r"\s*-\s*Anna.s Archive.*$", "", title), "author": txt("//div[contains(@class,'italic')][1]//text()") or None, "description": desc, "mirrors": mirrors[:10]}


def details_record(d: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    text = d["description"] or f"{d['title']} (no description available)"
    return content_record(f"book:{d['md5']}", "book", "book", [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": text}], url=f"{base_url()}/md5/{d['md5']}", title=d["title"],
                          author={"handle": d.get("author")}, raw_path=raw_path, fetch_method="browser", extra={"mirrors": d["mirrors"], "metadata_only": True},
                          source={"id": "book:site:annas-archive", "kind": "site", "title": "Anna's Archive", "url": base_url()})


class Annas(PlatformAdapter):
    platform = "book"
    capabilities = frozenset({"search", "fetch", "download"})
    opts = {"search": [(("--ext",), {"choices": ["pdf", "epub"]}), (("--lang",), {"default": "en"})]}

    def search(self, query, *, limit=15, since=None, ext=None, lang="en", **_):
        params = {"q": query, **({"ext": ext} if ext else {}), **({"lang": lang} if lang and lang != "all" else {})}
        final, html = _browser.load_html("book", f"{base_url()}/search?{urlencode(params)}", wait="domcontentloaded")
        if "check=1" in final or "ddos" in html[:3000].lower():
            raise CliError("CHECKPOINT", "Anna's Archive shows a DDoS-Guard check", "solve it once in the agent browser (agent_browser.py vnc) and retry")
        return parse_search(html, base_url())[:limit]

    def fetch(self, item, **_):
        md5 = md5_of(item)
        final, html = _browser.load_html("book", f"{base_url()}/md5/{md5}")
        return details_record(parse_details(html, md5, base_url()), save_raw("book", md5, html, "html"))

    def download(self, item: str, mirror: int = 0) -> dict[str, Any]:
        md5 = md5_of(item)
        final, html = _browser.load_html("book", f"{base_url()}/md5/{md5}")
        mirrors = parse_details(html, md5, base_url())["mirrors"]
        if not mirrors:
            raise CliError("NOT_FOUND", "no download mirrors found for this book")
        url = mirrors[min(mirror, len(mirrors) - 1)]["url"]
        dest_dir = config.data_dir() / "books"
        dest_dir.mkdir(parents=True, exist_ok=True)
        with browser.page("book", block=()) as pg:
            try:
                with pg.expect_download(timeout=120000) as dl:
                    pg.goto(url)
                    if not dl.is_set():
                        pg.wait_for_timeout(5000)
                d = dl.value
            except Exception as e:  # noqa: BLE001 - slow-download pages often wait or show a captcha
                raise CliError("CHECKPOINT", "the mirror did not start a download (wait page or captcha)", "open the mirror in the agent browser (vnc), then retry") from e
            ext = (d.suggested_filename.rsplit(".", 1) + ["pdf"])[1]
            path = dest_dir / f"{md5}.{ext}"
            d.save_as(str(path))
        return {"md5": md5, "path": str(path.relative_to(config.repo_root())), "next": f"uv run .agents/skills/document-reader/scripts/document.py fetch {path.relative_to(config.repo_root())} --source-id book:{md5}"}

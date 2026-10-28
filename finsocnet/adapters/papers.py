"""arXiv + Hugging Face Papers (specs/05 §2.13)."""

from __future__ import annotations

import re
from typing import Any

import feedparser

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, save_raw
from finsocnet.core.segments import paragraph_segments, refs

ARXIV = "https://export.arxiv.org/api/query"
HF = "https://huggingface.co/api"
ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


def arxiv_id(ref: str) -> tuple[str, str | None]:
    m = ID_RE.search(ref)
    if not m:
        raise CliError("USAGE", f"cannot read an arXiv id from {ref!r}", "use 2401.01234 or an arxiv.org URL")
    return m.group(1), m.group(2)


def hf_ref(p: dict[str, Any]) -> dict[str, Any]:
    paper = p.get("paper", p)
    return item_ref(f"https://arxiv.org/abs/{paper['id']}", f"arxiv:{paper['id']}", "paper", paper.get("title"), (paper.get("authors") or [{}])[0].get("name"),
                    (paper.get("publishedAt") or "")[:10], paper.get("summary"), {"upvotes": paper.get("upvotes"), "github_repo": paper.get("githubRepo")})


def parse_arxiv_feed(xml: str) -> list[dict[str, Any]]:
    out = []
    for e in feedparser.parse(xml).entries:
        aid, ver = arxiv_id(e.id)
        pdf = next((l.href for l in e.get("links", []) if l.get("title") == "pdf"), f"https://arxiv.org/pdf/{aid}")
        out.append({"id": aid, "version": ver, "title": " ".join(e.title.split()), "summary": " ".join(e.summary.split()), "authors": [a.name for a in e.get("authors", [])],
                    "published": e.get("published"), "category": (e.get("arxiv_primary_category") or {}).get("term") or (e.tags[0]["term"] if e.get("tags") else None), "pdf": pdf})
    return out


def build_record(p: dict[str, Any], github: str | None, raw_path: str | None) -> dict[str, Any]:
    segs = paragraph_segments(p["summary"], min_len=1) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": p["title"]}]
    r = refs(p["summary"])
    links = list(dict.fromkeys(r["links"] + ([github] if github else [])))
    return content_record(f"arxiv:{p['id']}", "arxiv", "paper", segs, url=f"https://arxiv.org/abs/{p['id']}", title=p["title"], author={"handle": p["authors"][0] if p["authors"] else None},
                          published_at=(p.get("published") or "")[:10] or None, language="en", links=links, mentions=p["authors"], raw_path=raw_path, fetch_method="arxiv_api",
                          extra={"authors": p["authors"], "version": p.get("version"), "category": p.get("category"), "pdf_url": p["pdf"], "github_repo": github},
                          source={"id": "arxiv:site:arxiv.org", "kind": "site", "title": "arXiv"})


class Papers(PlatformAdapter):
    platform = "arxiv"
    capabilities = frozenset({"search", "fetch", "trending"})
    opts = {"search": [(("--has-code",), {"action": "store_true"})], "fetch": [(("--pdf",), {"action": "store_true"})]}

    def search(self, query, *, limit=20, since=None, has_code=False, **_):
        d = http.get_json(f"{HF}/papers/search", platform="arxiv", params={"q": query, "limit": min(limit, 50)})
        items = [hf_ref(p) for p in d]
        if has_code:
            items = [i for i in items if i["metrics"].get("github_repo")]
        return [i for i in items if not since or (i["published_at"] or "") >= since][:limit]

    def trending(self, *, limit=10, has_code=False, **_):
        d = http.get_json(f"{HF}/daily_papers", platform="arxiv", params={"limit": min(limit * 3 if has_code else limit, 100)})
        items = [hf_ref(p) for p in d]
        return [i for i in items if not has_code or i["metrics"].get("github_repo")][:limit]

    def fetch(self, item, *, pdf=False, **_):
        aid, _v = arxiv_id(item)
        xml = http.get_text(ARXIV, platform="arxiv", params={"id_list": aid})
        papers = parse_arxiv_feed(xml)
        if not papers:
            raise CliError("NOT_FOUND", f"arXiv has no paper {aid}")
        github = None
        try:
            github = http.get_json(f"{HF}/papers/{aid}", platform="arxiv").get("githubRepo")
        except CliError:
            pass
        rec = build_record(papers[0], github, save_raw("arxiv", aid, xml, "xml"))
        if pdf:
            rec["extra"]["pdf_download_hint"] = f"uv run .agents/skills/document-reader/scripts/document.py fetch {papers[0]['pdf']} --source-id arxiv:{aid}"
        return rec

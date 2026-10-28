"""OpenAlex and Semantic Scholar (specs/05 §3.9). SSRN search goes through the agent browser (not implemented here)."""

from __future__ import annotations

import os
import re
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

OA = "https://api.openalex.org"
S2 = "https://api.semanticscholar.org/graph/v1"


def abstract_of(work: dict[str, Any]) -> str:
    inv = work.get("abstract_inverted_index") or {}
    if not inv:
        return ""
    words: dict[int, str] = {}
    for w, positions in inv.items():
        for p in positions:
            words[p] = w
    return " ".join(words[i] for i in sorted(words))


def paper_id(work: dict[str, Any]) -> str:
    ids = work.get("ids") or {}
    if ids.get("arxiv") or "arxiv.org" in (work.get("doi") or ""):
        m = re.search(r"(\d{4}\.\d{4,5})", ids.get("arxiv") or work.get("doi") or "")
        if m:
            return f"arxiv:{m.group(1)}"
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    return f"paper:doi:{doi.lower()}" if doi else f"paper:openalex:{work['id'].rsplit('/', 1)[-1]}"


def oa_ref(w: dict[str, Any]) -> dict[str, Any]:
    first = ((w.get("authorships") or [{}])[0].get("author") or {}).get("display_name")
    return item_ref(w.get("doi") or w["id"], paper_id(w), "paper", w.get("display_name") or w.get("title"), first, w.get("publication_date"), abstract_of(w)[:300],
                    {"citations": w.get("cited_by_count"), "year": w.get("publication_year")})


def build_record(w: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    abstract = abstract_of(w) or "(no abstract available)"
    authors = [(a.get("author") or {}).get("display_name") for a in w.get("authorships", [])]
    loc = w.get("primary_location") or {}
    r = refs(abstract)
    return content_record(
        paper_id(w), "paper" if not paper_id(w).startswith("arxiv:") else "arxiv", "paper", [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": abstract}],
        url=w.get("doi") or loc.get("landing_page_url") or w["id"], title=w.get("display_name") or w.get("title"), description=None,
        author={"handle": authors[0] if authors else None}, published_at=w.get("publication_date"), language=w.get("language"), metrics={"citations": w.get("cited_by_count")},
        links=r["links"], mentions=[a for a in authors if a], raw_path=raw_path, fetch_method="openalex",
        extra={"authors": authors, "year": w.get("publication_year"), "open_access_pdf": (w.get("open_access") or {}).get("oa_url") or loc.get("pdf_url"), "venue": (loc.get("source") or {}).get("display_name"),
               "openalex_id": w["id"]}, source={"id": "paper:site:openalex.org", "kind": "site", "title": "OpenAlex"})


class Research(PlatformAdapter):
    platform = "paper"
    capabilities = frozenset({"search", "profile", "fetch"})
    opts = {"search": [(("--provider",), {"default": "openalex", "choices": ["openalex", "s2"]}), (("--filter",), {})], "fetch": [(("--pdf",), {"action": "store_true"})]}

    def _oa(self, path: str, **params: Any) -> Any:
        if os.getenv("OPENALEX_MAILTO"):
            params["mailto"] = os.environ["OPENALEX_MAILTO"]
        return http.get_json(f"{OA}{path}", platform="paper", params=params or None)

    def search(self, query, *, limit=20, since=None, provider="openalex", filter=None, **_):
        if provider == "s2":
            d = http.get_json(f"{S2}/paper/search", platform="paper", params={"query": query, "limit": min(limit, 100), "fields": "title,abstract,authors,year,openAccessPdf,externalIds"})
            out = []
            for p in d.get("data", []):
                ext = p.get("externalIds") or {}
                pid = f"arxiv:{ext['ArXiv']}" if ext.get("ArXiv") else f"paper:doi:{ext['DOI'].lower()}" if ext.get("DOI") else f"paper:s2:{p['paperId']}"
                out.append(item_ref(f"https://www.semanticscholar.org/paper/{p['paperId']}", pid, "paper", p.get("title"), ((p.get("authors") or [{}])[0]).get("name"), str(p.get("year") or ""), p.get("abstract")))
            return out[:limit]
        flt = [filter] if filter else []
        if since:
            flt.append(f"from_publication_date:{since}")
        d = self._oa("/works", search=query, **{"per-page": min(limit, 50)}, **({"filter": ",".join(flt)} if flt else {}))
        return [oa_ref(w) for w in d.get("results", [])][:limit]

    def profile(self, target, **_):
        aid = target.rsplit("/", 1)[-1]
        a = self._oa(f"/authors/{aid}") if re.match(r"A\d+", aid) else self._oa("/authors", search=target)["results"][0]
        return profile_record("paper", f"paper:author:{a['id'].rsplit('/', 1)[-1]}", a["display_name"], display_name=a["display_name"], followers=None, profile_url=a["id"],
                              bio=", ".join(i["display_name"] for i in a.get("last_known_institutions", []) if i.get("display_name")) or None)

    def fetch(self, item, *, pdf=False, **_):
        key = item.strip()
        if re.match(r"^https?://doi.org/", key):
            key = "doi:" + key.split("doi.org/", 1)[1]
        if key.startswith("paper:doi:"):
            key = "doi:" + key[len("paper:doi:"):]
        if key.startswith("paper:openalex:"):
            key = key.rsplit(":", 1)[-1]
        if re.match(r"^10\.\d{4,}/", key):
            key = "doi:" + key
        w = self._oa(f"/works/{key}")
        raw = save_raw("paper", w["id"].rsplit("/", 1)[-1], w)
        rec = build_record(w, raw)
        if pdf:
            url = rec["extra"].get("open_access_pdf")
            if not url:
                raise CliError("NOT_FOUND", "no open-access PDF known for this work", "metadata only: use fetch without --pdf")
            rec["extra"]["pdf_download_hint"] = f"uv run .agents/skills/document-reader/scripts/document.py fetch {url} --source-id {rec['id']}"
        return rec

"""SEC EDGAR (docs/spec/05 §3.8). Every request carries SEC_USER_AGENT; the budget keeps us under 10 requests/s."""

from __future__ import annotations

import os
import re
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_paragraphs, paragraph_segments

DATA = "https://data.sec.gov"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"


def ua_headers() -> dict[str, str]:
    ua = os.getenv("SEC_USER_AGENT")
    if not ua:
        raise CliError("USAGE", "SEC_USER_AGENT is not set", 'put a contact in .env, e.g. SEC_USER_AGENT="FinSocNet you@example.com"')
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def cik10(x: str) -> str:
    m = re.search(r"(\d{1,10})$", x.replace("sec:cik:", ""))
    if not m:
        raise CliError("USAGE", f"cannot read a CIK from {x!r}")
    return m.group(1).zfill(10)


def filings(sub: dict[str, Any], forms: set[str] | None, since: str | None) -> list[dict[str, Any]]:
    r = sub["filings"]["recent"]
    out = []
    for i, acc in enumerate(r["accessionNumber"]):
        form, date = r["form"][i], r["filingDate"][i]
        if forms and form not in forms:
            continue
        if since and date < since:
            continue
        out.append({"accession": acc, "form": form, "date": date, "primary": r["primaryDocument"][i], "description": r.get("primaryDocDescription", [""] * len(r["form"]))[i]})
    return out


def filing_ref(cik: str, name: str, f: dict[str, Any]) -> dict[str, Any]:
    return item_ref(f"{ARCHIVES}/{int(cik)}/{f['accession'].replace('-', '')}/{f['primary']}", f"sec:{f['accession']}", "filing", f"{name} {f['form']} {f['date']}", name, f["date"], f["description"], {"form": f["form"]})


def parse_information_table(xml: str, top: int = 20) -> list[dict[str, Any]]:
    rows = []
    for blk in re.findall(r"<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>", xml, re.S):
        g = lambda tag: (re.search(rf"<(?:\w+:)?{tag}>\s*([^<]*?)\s*</(?:\w+:)?{tag}>", blk) or [None, ""])[1]
        rows.append({"issuer": g("nameOfIssuer"), "class": g("titleOfClass"), "value": int(g("value") or 0), "shares": int(g("sshPrnamt") or 0)})
    return sorted(rows, key=lambda r: -r["value"])[:top]


def holdings_paragraphs(holdings: list[dict[str, Any]], period: str | None) -> list[str]:
    return [f"13F holding {i}: {h['issuer']} ({h['class']}) value ${h['value']:,} with {h['shares']:,} shares" + (f" at {period}" if period else "") + "." for i, h in enumerate(holdings, 1)]


def build_record(cik: str, name: str, f: dict[str, Any], body_html: str, raw_path: str | None, holdings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    segs = html_paragraphs(body_html) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": f"{name} {f['form']} filed {f['date']}"}]
    extra: dict[str, Any] = {"form": f["form"], "cik": cik, "accession": f["accession"], "evidence_level_hint": "audited"}
    if holdings:
        extra["holdings"] = holdings
        for t in holdings_paragraphs(holdings, f["date"]):
            segs.append({"seq": len(segs), "kind": "paragraph", "locator": {"para": len(segs), "section": "13F holdings"}, "text": t})
    return content_record(f"sec:{f['accession']}", "sec", "filing", segs, url=f"{ARCHIVES}/{int(cik)}/{f['accession'].replace('-', '')}/{f['primary']}", title=f"{name} {f['form']} {f['date']}",
                          author={"handle": name}, published_at=f["date"], language="en", raw_path=raw_path, fetch_method="edgar", extra=extra,
                          source={"id": f"sec:cik:{cik}", "kind": "site", "title": name})


class SEC(PlatformAdapter):
    platform = "sec"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--forms",), {"default": "10-K,13F-HR"})], "list": [(("--forms",), {})]}

    def search(self, query, *, limit=20, since=None, forms="10-K,13F-HR", **_):
        d = http.get_json("https://efts.sec.gov/LATEST/search-index", platform="sec", headers=ua_headers(), params={"q": f'"{query}"', "forms": forms})
        out = []
        for h in d.get("hits", {}).get("hits", [])[:limit]:
            s = h["_source"]
            acc = s.get("adsh")
            out.append(item_ref(f"{ARCHIVES}/{int(s['ciks'][0])}/{acc.replace('-', '')}/", f"sec:{acc}", "filing", f"{(s.get('display_names') or [''])[0]} {s.get('form')}", None, s.get("file_date"), None, {"form": s.get("form")}))
        return out

    def _submissions(self, cik: str) -> dict[str, Any]:
        return http.get_json(f"{DATA}/submissions/CIK{cik}.json", platform="sec", headers=ua_headers())

    def profile(self, target, **_):
        cik = cik10(target)
        s = self._submissions(cik)
        return profile_record("sec", f"sec:cik:{cik}", s.get("name", cik), display_name=s.get("name"), bio=s.get("sicDescription"), profile_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                              links=[f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"])

    def list(self, source, *, limit=50, cursor=None, since=None, forms=None, **_):
        cik = cik10(source)
        s = self._submissions(cik)
        fl = filings(s, set(forms.split(",")) if forms else None, since)
        if cursor:
            fl = fl[[f["accession"] for f in fl].index(cursor) + 1:] if cursor in [f["accession"] for f in fl] else fl
        return list_result([filing_ref(cik, s["name"], f) for f in fl][:limit], fl[limit - 1]["accession"] if len(fl) > limit else None, {"id": f"sec:cik:{cik}"})

    def fetch(self, item, **_):
        acc = item.replace("sec:", "")
        m = re.search(r"/data/(\d+)/(\d{18})/([^/]+)$", item)
        if m:
            cik = m.group(1).zfill(10)
            acc = f"{m.group(2)[:10]}-{m.group(2)[10:12]}-{m.group(2)[12:]}"
        else:
            raise CliError("USAGE", "give the filing document URL as returned by list/search", "e.g. https://www.sec.gov/Archives/edgar/data/1067983/000095012325003211/xslForm13F_X02/primary_doc.xml")
        sub = self._submissions(cik)
        f = next((x for x in filings(sub, None, None) if x["accession"] == acc), None) or {"accession": acc, "form": "?", "date": "", "primary": m.group(3), "description": ""}
        body = http.get_text(item, platform="sec", headers=ua_headers())
        holdings = None
        if "13F" in f["form"]:
            try:
                tbl = http.get_text(item.rsplit("/", 1)[0].replace("xslForm13F_X02/", "") + "/informationtable.xml", platform="sec", headers=ua_headers())
                holdings = parse_information_table(tbl)
            except CliError:
                holdings = None
        return build_record(cik, sub.get("name", cik), f, body, save_raw("sec", acc, body, "html"), holdings)

"""Recipe-driven adapter: a new site, forum, blog, API or feed described in `config/sites/<name>.yaml` (specs/14-platform-skill-builder.md).

A recipe says where the lists are, how to pick items out of them (CSS selectors, JSON paths or feed entries) and where the text of one item
is; this class does the rest with the standard platform contract (search / profile / list / fetch, --ingest, known/visited flags). Most new
sites need no new Python: `platform-skill-builder` writes the recipe, tests it against the live site and wraps it in a skill folder.

Field expressions (HTML):   `css`            text of the first match
                            `css@attr`       attribute of the first match      (`@href` alone: the node itself)
                            `css|css2`       first expression that yields something
JSON (mode api):            `a.b.0.c`        dotted path; a leading `$.` is optional
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

import yaml
from lxml import html as lhtml

from finsocnet.core import config, http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_to_markdown, paragraph_segments, refs

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,24}$")
MODES = ("http", "browser", "api", "feed")


def recipe_path(name: str) -> Path:
    return config.repo_root() / "config" / "sites" / f"{name}.yaml"


def load_recipe(name: str) -> dict[str, Any]:
    p = recipe_path(name)
    if not NAME_RE.match(name) or not p.exists():
        raise CliError("NOT_FOUND", f"no recipe for {name!r}", "create config/sites/<name>.yaml with the `platform-skill-builder` skill")
    r = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    problems = validate_recipe(r)
    if problems:
        raise CliError("VALIDATION_ERROR", f"recipe {name} is invalid ({len(problems)} problem(s))", details=[{"path": a, "problem": b} for a, b in problems])
    return r


def validate_recipe(r: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not NAME_RE.match(str(r.get("name", ""))):
        out.append(("/name", "lowercase letters, digits and dashes, 2-25 characters, starting with a letter"))
    if not str(r.get("base_url", "")).startswith(("http://", "https://")):
        out.append(("/base_url", "an http(s) URL"))
    if r.get("mode") not in MODES:
        out.append(("/mode", f"one of {', '.join(MODES)}"))
    for op in ("search", "list"):
        spec = r.get(op)
        if spec is None:
            continue
        if "url" not in spec:
            out.append((f"/{op}/url", "required, may contain {query} / {source} / {cursor}"))
        if r.get("mode") != "feed" and "items" not in spec:
            out.append((f"/{op}/items", "selector (html) or path (api) of the item array"))
        if r.get("mode") != "feed" and "url" not in (spec.get("fields") or {}):
            out.append((f"/{op}/fields/url", "every item needs a url"))
    if "fetch" in r and r.get("mode") in ("http", "browser") and "body" not in r["fetch"]:
        out.append(("/fetch/body", "selector of the element that holds the text"))
    if not any(op in r for op in ("search", "list", "fetch")):
        out.append(("/", "define at least one of search, list, fetch"))
    return out


# --- extraction ---------------------------------------------------------------------------------------------

def _first(node: Any, expr: str | None, base: str = "") -> str | None:
    """Evaluate one field expression on an lxml node. See the module docstring."""
    if not expr:
        return None
    for alt in expr.split("|"):
        alt = alt.strip()
        css, _, attr = alt.partition("@")
        css = css.strip()
        try:
            els = node.cssselect(css) if css else [node]
        except Exception:  # noqa: BLE001 - bad selector
            raise CliError("VALIDATION_ERROR", f"bad selector {css!r} in the recipe") from None
        if css == "":
            els = [node]
        if not els:
            continue
        el = els[0]
        val = el.get(attr) if attr else " ".join("".join(el.itertext()).split())
        if val:
            return urljoin(base, val) if attr in ("href", "src") else val.strip()
    return None


def _path(obj: Any, expr: str | None) -> Any:
    if expr is None:
        return None
    cur = obj
    for part in expr.removeprefix("$.").removeprefix("$").split("."):
        if part == "":
            continue
        if isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def native_id(recipe: dict[str, Any], url: str) -> str:
    rx = (recipe.get("id") or {}).get("from_url")
    if rx:
        m = re.search(rx, url)
        if m:
            return re.sub(r"[^A-Za-z0-9._-]", "_", m.group(1))[:80]
    u = urlsplit(url)
    return hashlib.sha1(f"{u.netloc}{u.path}?{u.query}".encode()).hexdigest()[:14]


class SiteRecipe(PlatformAdapter):
    requires_session = False

    def __init__(self, recipe: dict[str, Any] | str) -> None:
        self.r = load_recipe(recipe) if isinstance(recipe, str) else recipe
        self.platform = self.r["name"]
        self.requires_session = bool(self.r.get("requires_session"))
        self.capabilities = frozenset(op for op in ("search", "profile", "list", "fetch") if op in self.r)
        self.base = self.r["base_url"].rstrip("/") + "/"

    # -- loading --
    def _load(self, url: str) -> tuple[str, str]:
        mode = self.r["mode"]
        if mode == "browser":
            from finsocnet.adapters import _browser
            return _browser.load_html(self.platform, url)
        return url, http.request("GET", url, platform=self.platform, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}).text

    def _json(self, url: str) -> Any:
        return http.get_json(url, platform=self.platform)

    def _fill(self, template: str, **kw: str) -> str:
        url = template
        for k, v in kw.items():
            url = url.replace("{" + k + "}", quote(str(v), safe="") if k in ("query", "cursor") else str(v))
        return urljoin(self.base, url)

    # -- items --
    def _items(self, spec: dict[str, Any], url: str, kind: str) -> tuple[list[dict[str, Any]], str | None]:
        mode = self.r["mode"]
        fields = spec.get("fields") or {}
        out: list[dict[str, Any]] = []
        nxt: str | None = None
        if mode == "feed":
            import feedparser
            f = feedparser.parse(http.request("GET", url, platform=self.platform).text)
            for e in f.entries:
                link = e.get("link") or ""
                if link:
                    out.append({"url": link, "title": e.get("title"), "author": e.get("author"), "date": e.get("published") or e.get("updated"),
                                "snippet": re.sub(r"<[^>]+>", " ", e.get("summary", ""))})
            return out, None
        if mode == "api":
            data = self._json(url)
            for row in _path(data, spec["items"]) or []:
                out.append({k: _path(row, v) for k, v in fields.items()})
            nxt = _path(data, spec.get("next"))
            return [o for o in out if o.get("url")], (str(nxt) if nxt else None)
        final, page = self._load(url)
        root = lhtml.fromstring(page)
        for node in root.cssselect(spec["items"]):
            out.append({k: _first(node, v, final) for k, v in fields.items()})
        if spec.get("next"):
            nxt = _first(root, spec["next"], final)
        return [o for o in out if o.get("url")], nxt

    def _ref(self, it: dict[str, Any], kind: str) -> dict[str, Any]:
        url = urljoin(self.base, str(it["url"]))
        return item_ref(url, f"{self.platform}:{native_id(self.r, url)}", it.get("kind") or kind, it.get("title"), it.get("author"), it.get("date"), it.get("snippet"))

    # -- contract --
    def search(self, query, *, limit=20, since=None, **_):
        spec = self.r["search"]
        items, _ = self._items(spec, self._fill(spec["url"], query=query), "post")
        return [self._ref(i, self.r.get("item_kind", "post")) for i in items][:limit]

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        spec = self.r["list"]
        url = cursor if cursor and cursor.startswith("http") else self._fill(spec["url"], source=source, cursor=cursor or "")
        items, nxt = self._items(spec, url, "post")
        if nxt and not str(nxt).startswith("http") and self.r["mode"] != "api":
            nxt = urljoin(self.base, str(nxt))
        return list_result([self._ref(i, self.r.get("item_kind", "post")) for i in items][:limit], nxt,
                           {"id": f"{self.platform}:{self.r.get('source_kind', 'site')}:{re.sub(r'[^a-z0-9._-]+', '-', source.lower()).strip('-')[:60] or 'main'}", "title": source})

    def profile(self, target, **_):
        spec = self.r.get("profile")
        if not spec:
            raise self._unsupported("profile")
        url = self._fill(spec["url"], target=target)
        if self.r["mode"] == "api":
            d = self._json(url)
            g = lambda k: _path(d, (spec.get("fields") or {}).get(k))  # noqa: E731
            return profile_record(self.platform, f"{self.platform}:{self.r.get('profile_kind', 'user')}:{target.lower()}", target, display_name=g("name") or target, bio=g("bio"),
                                  avatar_url=g("avatar"), profile_url=url, followers=g("followers"))
        final, page = self._load(url)
        root = lhtml.fromstring(page)
        f = spec.get("fields") or {}
        return profile_record(self.platform, f"{self.platform}:{self.r.get('profile_kind', 'user')}:{target.lower()}", target, display_name=_first(root, f.get("name"), final) or target,
                              bio=_first(root, f.get("bio"), final), avatar_url=_first(root, f.get("avatar"), final), profile_url=final)

    def fetch(self, item, **_):
        spec = self.r.get("fetch")
        if not spec:
            raise self._unsupported("fetch")
        url = item if item.startswith("http") else urljoin(self.base, item)
        nid = native_id(self.r, url)
        cid = f"{self.platform}:{nid}"
        if self.r["mode"] == "api":
            d = self._json(url if "{" not in spec.get("url", "") else self._fill(spec["url"], id=nid))
            body = _path(d, spec.get("body")) or ""
            title = _path(d, spec.get("title"))
            segs = paragraph_segments(html_to_markdown(body) if "<" in str(body) else str(body), min_len=1) or []
            if not segs:
                raise CliError("NOT_FOUND", f"{url} has no text at {spec.get('body')!r}", "check fetch.body in the recipe")
            author, date = _path(d, spec.get("author")), _path(d, spec.get("date"))
            raw = save_raw(self.platform, nid, d)
            comments_node: list[dict[str, Any]] = []
        else:
            final, page = self._load(url)
            root = lhtml.fromstring(page)
            body_nodes = root.cssselect(spec["body"])
            if not body_nodes:
                raise CliError("NOT_FOUND", f"no element matches fetch.body {spec['body']!r} on {final}", "adjust the selector in config/sites/<name>.yaml (see `site.py check`)")
            body_html = "\n".join(lhtml.tostring(n, encoding="unicode") for n in body_nodes)
            segs = paragraph_segments(html_to_markdown(body_html), min_len=1)
            title, author, date = _first(root, spec.get("title"), final), _first(root, spec.get("author"), final), _first(root, spec.get("date"), final)
            url = final
            raw = save_raw(self.platform, nid, page, "html")
            comments_node = []
            c = spec.get("comments")
            if c:
                for n in root.cssselect(c["items"]):
                    txt = _first(n, c.get("text"), final)
                    if txt:
                        comments_node.append({"author": _first(n, c.get("author"), final), "text": txt})
        segs = [{"seq": 0, "kind": "post" if i == 0 else "paragraph", "locator": {"para": i}, "text": s["text"], "author": {"handle": author} if (i == 0 and author) else None}
                for i, s in enumerate(segs)]
        for n, c in enumerate(comments_node):
            segs.append({"seq": 0, "kind": "comment", "locator": {"comment": n}, "author": {"handle": c["author"]} if c["author"] else None, "text": c["text"]})
        r = refs("\n".join(s["text"] for s in segs))
        host = urlsplit(url).netloc
        return content_record(cid, self.platform, self.r.get("content_type", "article"), segs, url=url, title=title, author={"handle": author} if author else None,
                              published_at=date, language=self.r.get("language"), links=r["links"][:300], mentions=r["mentions"], raw_path=raw,
                              fetch_method=f"recipe:{self.r['mode']}", extra={"recipe": self.platform},
                              source={"id": f"{self.platform}:{self.r.get('source_kind', 'site')}:{host}", "kind": self.r.get("source_kind", "site"), "title": self.r.get("title") or host, "url": self.base.rstrip("/")})

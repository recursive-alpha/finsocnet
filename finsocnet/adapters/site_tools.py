"""Helpers of `platform-skill-builder`: probe an unknown site, check a recipe against the live site, scaffold the skill folder
(specs/14-platform-skill-builder.md). Nothing here writes outside `config/sites/`, `config/platforms.yaml`, `config/budgets.yaml` and
`.agents/skills/<name>-explorer/`, and nothing logs in."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import yaml
from lxml import html as lhtml

from finsocnet.adapters import forum, site_recipe
from finsocnet.core import config, dispatch, http
from finsocnet.core.output import CliError

FEED_PATHS = ("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/index.xml", "/feeds/posts/default", "/?feed=rss2")
BOT_WALL = re.compile(r"just a moment|attention required|cf-chl|captcha|access denied|verify you are (a )?human|enable javascript and cookies", re.I)


def _get(url: str, **kw: Any):
    kw.setdefault("platform", "probe")
    try:
        return http.request("GET", url, platform=kw.pop("platform", "default"), retries=1, timeout=20, **kw)
    except CliError as e:
        return e


def _robots(base: str) -> dict[str, Any]:
    """robots.txt as it applies to a generic crawler (`User-agent: *`), grouped properly; flags a full block and content signals."""
    r = _get(urljoin(base, "/robots.txt"))
    if isinstance(r, CliError) or r.status_code != 200 or "<html" in r.text[:200].lower():
        return {"found": False}
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    sitemaps, signals = [], []
    for raw in r.text.splitlines():
        line = raw.split("#", 1)[0].strip()
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(v.lower())
        elif k in ("disallow", "allow", "crawl-delay") and agents:
            rules.append((k, v))
        elif k == "sitemap":
            sitemaps.append(v)
        elif k == "content-signal":
            signals.append(v)
    if agents:
        groups.append((agents, rules))
    star = [rl for ag, rl in groups if "*" in ag]
    rules_star = star[-1] if star else []
    dis = [v for k, v in rules_star if k == "disallow" and v]
    delay = next((v for k, v in rules_star if k == "crawl-delay"), None)
    return {"found": True, "blocks_everything": "/" in dis, "disallow_for_all": dis[:25], "crawl_delay": delay, "content_signals": signals[:3], "sitemaps": sitemaps[:5]}


def _repeating_blocks(root: Any, base: str) -> list[dict[str, Any]]:
    """Candidate item selectors: elements that repeat and each hold a link with a headline-like text."""
    counts: Counter[str] = Counter()
    sample: dict[str, str] = {}
    for a in root.cssselect("a[href]"):
        text = " ".join("".join(a.itertext()).split())
        if len(text) < 15:
            continue
        node = a
        for _ in range(4):  # climb to the repeated container
            node = node.getparent()
            if node is None or node.tag in ("body", "html"):
                break
            cls = ".".join(sorted(c for c in (node.get("class") or "").split() if re.match(r"^[A-Za-z][\w-]{2,30}$", c)))[:60]
            if cls:
                key = f"{node.tag}.{cls}"
                counts[key] += 1
                sample.setdefault(key, text[:80])
    return [{"items": k, "count": n, "sample_title": sample[k]} for k, n in counts.most_common(4) if n >= 4]


def probe(url: str) -> dict[str, Any]:
    """Facts about a site and a recommended strategy. Plain HTTP only (no browser, no login); `needs_browser` says when that was not enough."""
    u = urlsplit(url if "://" in url else "https://" + url)
    base = f"{u.scheme}://{u.netloc}/"
    out: dict[str, Any] = {"url": url, "host": u.netloc, "existing_skill": dispatch.classify(url if "://" in url else "https://" + url)}
    r = _get(url if "://" in url else "https://" + url, platform="probe")
    if isinstance(r, CliError):
        return {**out, "reachable": False, "error": {"code": r.code, "message": r.message}, "strategy": "browser", "notes": ["plain HTTP failed; try the agent browser (mode: browser) or ask the user"]}
    html = r.text
    out.update(reachable=True, status=r.status_code, final_url=str(r.url), content_type=r.headers.get("content-type", ""), server=r.headers.get("server"), bytes=len(r.content))
    notes: list[str] = []
    if BOT_WALL.search(html[:6000]) or r.status_code in (403, 429, 503):
        notes.append("bot wall or error status: use the agent browser (mode: browser), and expect checkpoints")
        out["bot_wall"] = True
    try:
        root = lhtml.fromstring(html)
    except Exception:  # noqa: BLE001
        root = None
    out["robots"] = _robots(base)
    if out["robots"].get("blocks_everything"):
        notes.append("robots.txt disallows everything for generic crawlers: do NOT build a scraper; ask the user (an official API, an export, or their explicit decision)")
    elif out["robots"].get("content_signals"):
        notes.append(f"robots.txt content signals: {out['robots']['content_signals'][0]} — read them and tell the user before collecting")
    if out["robots"].get("crawl_delay"):
        notes.append(f"robots.txt asks for a crawl delay of {out['robots']['crawl_delay']}s: set budget.min_delay_ms accordingly in the recipe")
    feeds: list[str] = []
    if root is not None:
        feeds = [urljoin(str(r.url), h) for h in root.xpath("//link[@rel='alternate'][contains(@type,'rss') or contains(@type,'atom')]/@href")]
        out["title"] = (root.xpath("//title/text()") or [""])[0].strip()
        gen = (root.xpath("//meta[@name='generator']/@content") or [None])[0]
        out["generator"] = gen
        text_len = len(" ".join(root.text_content().split()))
        out["text_chars"] = text_len
        out["has_password_field"] = bool(root.xpath("//input[@type='password']"))
        out["looks_js_rendered"] = text_len < 800 and len(html) > 20000
        out["candidate_item_selectors"] = _repeating_blocks(root, str(r.url))
        out["json_ld_types"] = sorted({m for m in re.findall(r'"@type"\s*:\s*"(\w+)"', html[:200000])})[:8]
        if out["looks_js_rendered"]:
            notes.append("page looks JavaScript-rendered (little text, much markup): use mode: browser or find the JSON API in the network log")
        if out["has_password_field"] and text_len < 1500:
            notes.append("login form and almost no text: probably requires a session; ask the user (session-bridge), never ask for a password")
    for p in FEED_PATHS if not feeds else ():
        fr = _get(urljoin(base, p))
        if not isinstance(fr, CliError) and fr.status_code == 200 and re.search(r"<(rss|feed|rdf)\b", fr.text[:800], re.I):
            feeds.append(urljoin(base, p))
            break
    out["feeds"] = list(dict.fromkeys(feeds))[:5]
    engines: dict[str, Any] = {}
    eng = forum.detect_engine(html, url)
    if eng != "generic":
        engines["forum"] = eng
    for name, path, marker in (("wordpress", "/wp-json/", '"namespaces"'), ("discourse_json", "/latest.json", '"topic_list"'), ("mastodon", "/api/v1/instance", '"uri"'),
                               ("lemmy", "/api/v3/site", '"site_view"'), ("ghost", "/ghost/api/content/posts/", '"errors"')):
        pr = _get(urljoin(base, path))
        if not isinstance(pr, CliError) and pr.status_code in (200, 401, 403) and marker in pr.text[:4000]:
            engines[name] = urljoin(base, path)
    out["engines"] = engines
    rec = out["existing_skill"]
    if rec["platform"] not in ("web", "") and rec["skill"] != "web-reader":
        strategy = "existing"
        notes.append(f"already covered by {rec['skill']}: use it; build a new skill only if you need something it does not do")
    elif "forum" in engines:
        strategy = "existing"
        notes.append("a forum engine was detected: forum-explorer handles it (forum.py list/fetch), no new skill needed")
    elif "wordpress" in engines:
        strategy = "api"
        notes.append("WordPress REST API: mode api, list url /wp-json/wp/v2/posts?per_page=50&search={query}, items '', fields url=link title=title.rendered date=date")
    elif out["feeds"]:
        strategy = "feed"
        notes.append("a feed exists: mode feed lists items cheaply; fetch.body must still be a selector for the article page")
    elif out.get("bot_wall") or out.get("looks_js_rendered"):
        strategy = "browser"
    else:
        strategy = "http"
    if out["robots"].get("blocks_everything"):
        strategy = "blocked"
    out["strategy"] = strategy
    out["notes"] = notes
    out["next"] = ["ask the user what to collect (whole site, one section, one account) and whether any part needs a login",
                   "write config/sites/<name>.yaml (see references/recipe.md), then `site.py check <name>`"]
    return out


# --- check ---------------------------------------------------------------------------------------------------------

def check(name: str, *, query: str | None = None, source: str | None = None, item: str | None = None, target: str | None = None) -> dict[str, Any]:
    """Run each defined operation of the recipe against the live site and report what each field matched, so selectors can be fixed."""
    ad = site_recipe.SiteRecipe(name)
    rep: dict[str, Any] = {"recipe": name, "mode": ad.r["mode"], "operations": {}, "problems": []}
    first_url = item

    def summarize(label: str, items: list[dict[str, Any]]) -> None:
        nonlocal first_url
        n = len(items)
        info = {"count": n, "with_title": sum(1 for i in items if i.get("title")), "with_author": sum(1 for i in items if i.get("author_handle")),
                "with_date": sum(1 for i in items if i.get("published_at")), "sample": [{"id": i["id"], "title": (i.get("title") or "")[:80], "ref": i["ref"]} for i in items[:3]]}
        rep["operations"][label] = info
        if n == 0:
            rep["problems"].append(f"{label}: no items; check {label}.url and {label}.items")
        elif info["with_title"] == 0:
            rep["problems"].append(f"{label}: items found but no titles; check {label}.fields.title")
        if items:
            first_url = first_url or items[0]["ref"]

    try:
        if "search" in ad.r and query:
            summarize("search", ad.search(query, limit=10))
        elif "search" in ad.r:
            rep["operations"]["search"] = {"skipped": "give --query"}
        if "list" in ad.r and source is not None:
            res = ad.list(source, limit=10)
            summarize("list", res["items"])
            rep["operations"]["list"]["next_cursor"] = res.get("next_cursor")
        elif "list" in ad.r:
            rep["operations"]["list"] = {"skipped": "give --source"}
        if "fetch" in ad.r and first_url:
            rec = ad.fetch(first_url)
            body = " ".join(s["text"] for s in rec["segments"])
            rep["operations"]["fetch"] = {"url": rec["url"], "id": rec["id"], "title": rec.get("title"), "author": (rec.get("author") or {}).get("handle"), "published_at": rec.get("published_at"),
                                          "segments": len(rec["segments"]), "chars": len(body), "preview": body[:240]}
            if len(body) < 200:
                rep["problems"].append("fetch: very little text; fetch.body probably points at the wrong element")
            if not rec.get("title"):
                rep["problems"].append("fetch: no title; check fetch.title")
        elif "fetch" in ad.r:
            rep["operations"]["fetch"] = {"skipped": "no item URL available: give --item or --query/--source"}
        if "profile" in ad.r and target:
            p = ad.profile(target)
            rep["operations"]["profile"] = {"display_name": p.get("display_name"), "bio": (p.get("bio") or "")[:120], "avatar_url": p.get("avatar_url")}
    except CliError as e:
        rep["problems"].append(f"{e.code}: {e.message}")
    rep["ok"] = not rep["problems"]
    return rep


# --- scaffold ------------------------------------------------------------------------------------------------------

SKILL_TMPL = """---
name: {name}-explorer
description: Explore {title} ({base}) — {ops_sentence} — and store the items as FinSocNet content. Use for {host} links and for "{name}" requests. Created by platform-skill-builder from config/sites/{name}.yaml.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI){browser_note}.
metadata:
  author: finsocnet
  version: "1.0.0"
  priority: "P3"
  status: ready
  phase: "9"
  spec: specs/14-platform-skill-builder.md
---

# {title} explorer

Recipe: `config/sites/{name}.yaml` (mode `{mode}`{session_note}). Items are stored as content ids `{name}:<native id>`, sources as `{name}:{source_kind}:<name>`.

```bash
S=.agents/skills/{name}-explorer/scripts/{name}.py
{commands}
```

Common flags (specs/00 §3): `--ingest --run R` stores the record, `--enqueue --run R` queues unseen items, `--save-cursor` keeps the list position, `--new-only` hides items already fetched or skipped, `--no-track` leaves `seen_items` alone, `--full` prints the whole record.

## Procedure

1. `kb run start --skill {name}-explorer --goal "<what>" …` → `R`.
2. `list`/`search` with `--run R` (sightings are tracked); judge the items; `kb seen mark --key <id> --status skipped --note "<why>"` for the irrelevant ones.
3. `fetch <url> --ingest --run R`, then `market-idea-miner` on the content id when it holds knowledge (for non-English text use `translator` first).
4. Exit 3 means a login or checkpoint: stop and tell the user which session export to redo. Exit 4: wait `retry_after_sec`.

## When it breaks

The site changed its markup if `fetch` fails with `NOT_FOUND ... fetch.body` or lists come back empty: run `uv run .agents/skills/platform-skill-builder/scripts/site.py check {name} --source <x>` and fix the selectors in the recipe (see `platform-skill-builder`); record what changed in `references/platform_notes.md`.

## References

- `references/platform_notes.md` — what was verified, selectors, quirks.
"""

WRAPPER = '''#!/usr/bin/env python3
"""{title} CLI, driven by config/sites/{name}.yaml (specs/14-platform-skill-builder.md)."""

from finsocnet.adapters.site_recipe import SiteRecipe
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(SiteRecipe("{name}"))
'''


def scaffold(name: str, *, force: bool = False) -> dict[str, Any]:
    r = site_recipe.load_recipe(name)
    root = config.repo_root()
    skill = root / ".agents" / "skills" / f"{name}-explorer"
    if skill.exists() and not force:
        raise CliError("CONFLICT", f"{skill.relative_to(root)} already exists", "pass --force to rewrite the generated files (platform_notes.md is kept)")
    host = urlsplit(r["base_url"]).netloc
    ad = site_recipe.SiteRecipe(r)
    ops = [o for o in ("search", "profile", "list", "fetch") if o in ad.capabilities]
    cmd_lines = {"search": 'uv run $S search "<query>" [--limit N] [--new-only]', "profile": "uv run $S profile <target> [--ingest --run R]",
                 "list": "uv run $S list <source> [--limit N] [--cursor C] [--save-cursor] [--enqueue] [--new-only]", "fetch": "uv run $S fetch <url> [--ingest --run R] [--full]"}
    text = SKILL_TMPL.format(name=name, title=r.get("title") or host, base=r["base_url"], host=host, mode=r["mode"], source_kind=r.get("source_kind", "site"),
                             ops_sentence=" / ".join(ops), commands="\n".join(cmd_lines[o] for o in ops),
                             session_note=", requires the user's imported session" if r.get("requires_session") else "",
                             browser_note=" and the agent browser" if r["mode"] == "browser" else "")
    (skill / "scripts").mkdir(parents=True, exist_ok=True)
    (skill / "references").mkdir(exist_ok=True)
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    w = skill / "scripts" / f"{name}.py"
    w.write_text(WRAPPER.format(name=name, title=r.get("title") or host), encoding="utf-8")
    w.chmod(0o755)
    notes = skill / "references" / "platform_notes.md"
    if not notes.exists():
        notes.write_text(f"# {r.get('title') or host} — platform notes\n\n- Recipe: `config/sites/{name}.yaml` (mode `{r['mode']}`).\n- Created by `platform-skill-builder`; probe facts and the first `site.py check` result go here.\n", encoding="utf-8")
    added = []
    plat = root / "config" / "platforms.yaml"
    if f"\n{name}:" not in "\n" + plat.read_text(encoding="utf-8"):
        block = f"\n{name}:\n  requires_session: {'true' if r.get('requires_session') else 'false'}\n  domains: [{host.removeprefix('www.')}]\n  refresh_hours: {r.get('refresh_hours', 168)}\n"
        if r.get("requires_session"):
            block += f"  session_cookies: {r.get('session_cookies', [])}\n  probe_url: {r.get('probe_url', r['base_url'])}\n"
        plat.write_text(plat.read_text(encoding="utf-8").rstrip("\n") + "\n" + block, encoding="utf-8")
        added.append("config/platforms.yaml")
    bud = root / "config" / "budgets.yaml"
    if r.get("budget") and not re.search(rf"^{re.escape(name)}:", bud.read_text(encoding="utf-8"), re.M):
        b = r["budget"]
        bud.write_text(bud.read_text(encoding="utf-8").rstrip("\n") + f"\n{name}: {{per_minute: {b.get('per_minute', 10)}, per_hour: {b.get('per_hour', 200)}, per_day: {b.get('per_day', 2000)}, "
                       f"min_delay_ms: {b.get('min_delay_ms', 1000)}, max_delay_ms: {b.get('max_delay_ms', 3000)}}}\n", encoding="utf-8")
        added.append("config/budgets.yaml")
    return {"skill": str(skill.relative_to(root)), "files": ["SKILL.md", f"scripts/{name}.py", "references/platform_notes.md"], "config_updated": added,
            "next": ["run `uv run finsocnet install all` so harnesses that link skills one by one see it", "git status shows the new folder and config changes: review and commit"]}

"""Recipe-driven adapter, custom platforms and the builder tools (specs/14-platform-skill-builder.md)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import yaml

from finsocnet.adapters import site_recipe, site_tools
from finsocnet.core import dispatch, http, ids
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors

FX = Path(__file__).resolve().parents[1] / "fixtures" / "sites"

HTML_RECIPE = {
    "name": "exblog", "title": "Example Blog", "base_url": "https://blog.example", "mode": "http", "source_kind": "blog", "language": "en",
    "id": {"from_url": r"/\d{4}/\d{2}/([\w-]+)/"},
    "search": {"url": "/search?q={query}", "items": "article.post", "fields": {"url": "h2 a@href", "title": "h2 a", "author": ".by", "date": "time@datetime", "snippet": "p"}},
    "list": {"url": "/{source}/", "items": "article.post", "next": "a.next@href", "fields": {"url": "h2 a@href", "title": "h2 a", "author": ".by", "date": "time@datetime"}},
    "fetch": {"title": "h1", "author": ".author", "date": "time@datetime", "body": "div.content", "comments": {"items": "li.c", "author": ".u", "text": ".t"}},
    "dispatch": [{"pattern": r"blog\.example/\d{4}/", "action": "fetch"}],
}
API_RECIPE = {
    "name": "exapi", "base_url": "https://api.example", "mode": "api", "content_type": "post", "id": {"from_url": r"/posts/(\d+)"},
    "list": {"url": "/v1/posts?cursor={cursor}", "items": "data.posts", "next": "data.next", "fields": {"url": "slug", "title": "title", "author": "author.name", "date": "created"}},
    "fetch": {"url": "/v1/posts/{id}", "title": "data.posts.0.title", "author": "data.posts.0.author.name", "date": "data.posts.0.created", "body": "data.posts.0.html"},
}


@pytest.fixture
def web():
    pages = {"/search": ("text/html", (FX / "blog_index.html").read_text()), "/news/": ("text/html", (FX / "blog_index.html").read_text()),
             "/2026/10/pairs-trading-notes/": ("text/html", (FX / "blog_post.html").read_text()), "/v1/posts": ("application/json", (FX / "api_posts.json").read_text())}

    def handler(req: httpx.Request) -> httpx.Response:
        for path, (ctype, body) in pages.items():
            if req.url.path.startswith(path):
                return httpx.Response(200, headers={"content-type": ctype}, text=body)
        return httpx.Response(404, text="nope")

    http.set_transport(httpx.MockTransport(handler))
    yield
    http.set_transport(None)


def test_recipe_validation_reports_every_problem():
    probs = dict(site_recipe.validate_recipe({"name": "Bad Name", "base_url": "ftp://x", "mode": "magic", "list": {}}))
    assert {"/name", "/base_url", "/mode", "/list/url"} <= set(probs)
    assert site_recipe.validate_recipe(HTML_RECIPE) == [] and site_recipe.validate_recipe(API_RECIPE) == []


def write_recipes(repo):
    d = repo / "config" / "sites"
    d.mkdir(parents=True, exist_ok=True)
    for r in (HTML_RECIPE, API_RECIPE):
        (d / f"{r['name']}.yaml").write_text(yaml.safe_dump(r))


def test_html_list_search_and_fetch(web, repo):
    write_recipes(repo)
    ad = site_recipe.SiteRecipe(HTML_RECIPE)
    res = ad.list("news", limit=10)
    assert [i["title"] for i in res["items"]] == ["Pairs trading notes", "Risk sizing", "Elsewhere"]
    assert res["items"][0]["ref"] == "https://blog.example/2026/10/pairs-trading-notes/" and res["items"][0]["id"] == "exblog:pairs-trading-notes"
    assert res["items"][0]["author_handle"] == "Ana" and res["items"][0]["published_at"] == "2026-10-20" and res["next_cursor"] == "https://blog.example/page/2/"
    assert res["source"]["id"] == "exblog:blog:news"
    assert len(ad.search("pairs")) == 3
    rec = ad.fetch("https://blog.example/2026/10/pairs-trading-notes/")
    assert schema_errors("content_record", rec) == []
    assert rec["id"] == "exblog:pairs-trading-notes" and rec["title"] == "Pairs trading notes" and rec["author"]["handle"] == "Ana" and rec["published_at"] == "2026-10-20"
    kinds = [s["kind"] for s in rec["segments"]]
    assert kinds[0] == "post" and kinds.count("comment") == 2 and "https://example.org/ref" in rec["links"]
    assert rec["segments"][-1]["author"] == {"handle": "cy"} and rec["source"]["kind"] == "blog"


def test_api_mode_and_next_cursor(web, repo):
    write_recipes(repo)
    ad = site_recipe.SiteRecipe(API_RECIPE)
    res = ad.list("main", limit=5)
    assert [i["title"] for i in res["items"]] == ["Risk talk", "Tilt"] and res["next_cursor"] == "cursor-2"
    rec = ad.fetch("https://api.example/posts/7")
    assert rec["id"] == "exapi:7" and rec["title"] == "Risk talk" and "define the stop before the entry" in rec["segments"][0]["text"] and rec["content_type"] == "post"


def test_wrong_selector_is_a_pointed_error(web):
    bad = {**HTML_RECIPE, "fetch": {**HTML_RECIPE["fetch"], "body": "div.nothing"}}
    with pytest.raises(CliError) as e:
        site_recipe.SiteRecipe(bad).fetch("https://blog.example/2026/10/pairs-trading-notes/")
    assert e.value.code == "NOT_FOUND" and "fetch.body" in e.value.message


def test_check_reports_problems_per_operation(web, repo):
    (repo / "config" / "sites").mkdir(parents=True, exist_ok=True)
    (repo / "config" / "sites" / "exblog.yaml").write_text(yaml.safe_dump(HTML_RECIPE))
    ok = site_tools.check("exblog", query="pairs", source="news")
    assert ok["ok"] and ok["operations"]["list"]["count"] == 3 and ok["operations"]["fetch"]["segments"] >= 3
    broken = {**HTML_RECIPE, "list": {**HTML_RECIPE["list"], "items": "div.nothing"}}
    (repo / "config" / "sites" / "exbad.yaml").write_text(yaml.safe_dump({**broken, "name": "exbad"}))
    bad = site_tools.check("exbad", source="news")
    assert not bad["ok"] and any("no items" in p for p in bad["problems"])


def test_custom_platform_is_known_to_ids_dispatch_and_schema(repo):
    (repo / "config" / "sites").mkdir(parents=True, exist_ok=True)
    (repo / "config" / "sites" / "exblog.yaml").write_text(yaml.safe_dump(HTML_RECIPE))
    assert "exblog" in ids.known_platforms() and ids.content_id("exblog", "x") == "exblog:x"
    assert dispatch.classify("https://blog.example/2026/10/pairs-trading-notes/") == {"target_kind": "url", "platform": "exblog", "skill": "exblog-explorer", "action": "fetch"}
    assert dispatch.classify("https://blog.example/")["action"] == "list"
    assert dispatch.classify("https://unknown.example/")["platform"] == "web"
    rec = {"id": "nosuch:1", "platform": "nosuch", "content_type": "article", "segments": [{"seq": 0, "kind": "paragraph", "text": "x"}], "fetched_at": "2026-10-28T00:00:00Z"}
    assert any("unknown platform" in e["problem"] for e in schema_errors("content_record", rec))


def test_scaffold_writes_the_skill_folder_and_config(repo):
    (repo / "config" / "sites").mkdir(parents=True, exist_ok=True)
    (repo / "config" / "sites" / "exblog.yaml").write_text(yaml.safe_dump({**HTML_RECIPE, "budget": {"per_minute": 6}}))
    (repo / "config" / "platforms.yaml").write_text("x:\n  requires_session: true\n")
    (repo / "config" / "budgets.yaml").write_text("default: {per_minute: 20}\n")
    res = site_tools.scaffold("exblog")
    skill = repo / ".agents" / "skills" / "exblog-explorer"
    assert (skill / "SKILL.md").exists() and (skill / "scripts" / "exblog.py").exists() and res["config_updated"] == ["config/platforms.yaml", "config/budgets.yaml"]
    text = (skill / "SKILL.md").read_text()
    fm = yaml.safe_load(text.split("---", 2)[1])
    assert fm["name"] == "exblog-explorer" and len(fm["description"]) < 1024 and "search" in text and "list" in text and "profile" not in text.split("```bash")[1].split("```")[0]
    assert yaml.safe_load((repo / "config" / "platforms.yaml").read_text())["exblog"]["domains"] == ["blog.example"]
    with pytest.raises(CliError) as e:
        site_tools.scaffold("exblog")
    assert e.value.code == "CONFLICT"
    site_tools.scaffold("exblog", force=True)


def test_probe_finds_feeds_engines_and_blocking_robots(repo):
    def handler(req: httpx.Request) -> httpx.Response:
        p = req.url.path
        if p == "/robots.txt":
            return httpx.Response(200, text="User-agent: Googlebot\nAllow: /\n\nUser-agent: *\nCrawl-delay: 2\nDisallow: /\n\nContent-Signal: ai-train=no\n")
        if p == "/":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='<html><head><title>T</title><link rel="alternate" type="application/rss+xml" href="/rss"></head><body>' + "<article class='story'><a href='/a1'>A long headline number one</a></article>" * 5 + "</body></html>")
        return httpx.Response(404, text="no")

    http.set_transport(httpx.MockTransport(handler))
    try:
        out = site_tools.probe("https://blocked.example/")
    finally:
        http.set_transport(None)
    assert out["feeds"] == ["https://blocked.example/rss"] and out["robots"]["blocks_everything"] is True and out["robots"]["crawl_delay"] == "2"
    assert out["strategy"] == "blocked" and any("do NOT build a scraper" in n for n in out["notes"])
    assert out["candidate_item_selectors"][0]["items"] == "article.story"

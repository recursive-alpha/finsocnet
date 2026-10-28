"""Browser-based adapters: parsing with hand-written fixtures in the documented shape of each site (NOT recorded from the live
sites: those need accounts or block our network; see references/platform_notes.md), plus the real agent browser on a local page."""

from __future__ import annotations

import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from finsocnet.core import browser_proc
from finsocnet.core.output import CliError
from tests.integration.test_adapters_api import valid

ARTICLE_HTML = """<!doctype html><html><head><title>Trailing stops explained</title><link rel="canonical" href="https://example.org/blog/trailing-stops/?utm_source=x">
<meta name="author" content="Jane Trader"><meta name="description" content="How to trail"></head><body><nav>Menu Home About</nav><article><h1>Trailing stops explained</h1>
<p>A trailing stop follows the price and locks in gains once a trade works. Many swing traders trail the 10-day moving average and exit on a close below it.</p>
<p>Others prefer structure: raise the stop under each higher low. Whatever the method, write it down before entering the trade, and follow https://example.org/rules for details.</p>
<iframe src="https://www.youtube.com/embed/B1ALxAVtFfI"></iframe><video><track src="/captions/en.vtt" kind="captions"></video>
<a href="https://other.com/guide.pdf">Guide PDF</a><a href="https://other.com/page">Other</a></article><footer>Copyright</footer></body></html>"""


def test_web_page_record_and_discovery(repo):
    from finsocnet.adapters import web
    rec = valid(web.page_record("https://example.org/blog/trailing-stops/", ARTICLE_HTML))
    assert rec["platform"] == "web" and rec["title"] == "Trailing stops explained" and rec["url"] == "https://example.org/blog/trailing-stops"
    assert rec["id"].startswith("web:") and "Menu Home" not in " ".join(s["text"] for s in rec["segments"]) and "https://example.org/rules" in rec["links"]
    assert {m["kind"] for m in rec["media"]} == {"embed", "caption_track"} and rec["source"]["id"] == "web:site:example.org"
    items = web.discover_page(ARTICLE_HTML, "https://example.org/blog/")
    kinds = {i["kind"] for i in items}
    assert {"document", "outbound", "media", "caption_track"} <= kinds
    thin = web.page_record("https://x.org/a", "<html><body><div>tiny</div></body></html>")
    assert valid(thin)["segments"][0]["text"]


def test_google_parser_ignores_ads_and_unwraps_redirects():
    from finsocnet.adapters import google
    html = """<html><body><div id="tads"><a href="https://ad.com/x"><h3>Ad result</h3></a></div><div id="search"><div class="g"><a href="/url?q=https://example.com/orb&sa=U"><h3>Opening range breakout guide</h3></a>
    <div class="VwiC3b">Mar 3, 2025 — The opening range breakout is a simple intraday strategy with many variants and a lot of discussion.</div></div>
    <div class="g"><a href="https://www.google.com/search?q=related"><h3>Related searches</h3></a></div>
    <div class="g"><a href="https://site.org/p"><h3>Second</h3></a><div class="VwiC3b">A second snippet that is long enough to count as text here, honestly.</div></div></div></body></html>"""
    items = google.parse_results(html)
    assert [i["ref"] for i in items] == ["https://example.com/orb", "https://site.org/p"]
    assert items[0]["published_at"] == "Mar 3, 2025" and items[0]["title"] == "Opening range breakout guide"


def test_google_sorry_page_is_a_checkpoint(repo):
    from finsocnet.core import browser
    assert browser.classify_page("google", "https://www.google.com/sorry/index?continue=x", "unusual traffic from your network")[0] == "CHECKPOINT"


REDDIT_THREAD = [
    {"kind": "Listing", "data": {"children": [{"kind": "t3", "data": {"id": "1xg9xq1", "name": "t3_1xg9xq1", "title": "How I size after a losing streak", "selftext": "I cut size in half. See https://example.com/sizing", "author": "example_dt",
                                                                     "author_fullname": "t2_abc", "subreddit": "RealDayTrading", "permalink": "/r/RealDayTrading/comments/1xg9xq1/how/", "created_utc": 1789000000, "score": 412,
                                                                     "num_comments": 5, "url": "https://x", "over_18": False, "link_flair_text": "Risk"}}]}},
    {"kind": "Listing", "data": {"children": [
        {"kind": "t1", "data": {"id": "k1", "name": "t1_k1", "author": "other", "body": "Same here &amp; it saves me", "score": 87, "parent_id": "t3_1xg9xq1", "depth": 0,
                                "replies": {"kind": "Listing", "data": {"children": [{"kind": "t1", "data": {"id": "k2", "name": "t1_k2", "author": "example_dt", "body": "Glad it helps", "score": 3, "parent_id": "t1_k1", "depth": 1, "replies": ""}}]}}}},
        {"kind": "t1", "data": {"id": "k3", "name": "t1_k3", "author": "[deleted]", "body": "[deleted]", "score": 1, "parent_id": "t3_1xg9xq1", "depth": 0, "replies": ""}},
        {"kind": "more", "data": {"children": ["k4", "k5"], "count": 2}}]}},
]


def test_reddit_thread_record_and_listing():
    from finsocnet.adapters import reddit as rd
    warnings = []
    rec = valid(rd.build_record(REDDIT_THREAD, None, 500, warnings, None))
    assert rec["id"] == "reddit:1xg9xq1" and rec["segments"][0]["kind"] == "post" and rec["source"]["id"] == "reddit:subreddit:realdaytrading"
    c = [s for s in rec["segments"] if s["kind"] == "comment"]
    assert c[0]["locator"] == {"comment_id": "t1_k1", "parent_id": "t3_1xg9xq1", "score": 87, "depth": 0} and c[0]["text"] == "Same here & it saves me"
    assert c[1]["locator"]["parent_id"] == "t1_k1" and any(s["text"] == "[deleted]" and s["author"]["handle"] is None for s in c)
    assert any("more comments" in w for w in warnings) and "https://example.com/sizing" in rec["links"]
    capped = []
    rd.build_record(REDDIT_THREAD, None, 2, capped, None)
    assert any("cap 2 reached" in w for w in capped)
    listing = {"data": {"after": "t3_zzz", "children": [{"kind": "t3", "data": REDDIT_THREAD[0]["data"]["children"][0]["data"]}]}}
    assert rd.listing_refs(listing)[0]["id"] == "reddit:1xg9xq1" and rd.post_id("https://www.reddit.com/r/x/comments/1xg9xq1/slug/") == "1xg9xq1"


def gql_tweet(rest_id, text, uid="1", handle="Qullamaggie", conv=None, reply_to=None, likes=0, quoted=None, note=None):
    t = {"rest_id": rest_id, "core": {"user_results": {"result": {"rest_id": uid, "core": {"screen_name": handle, "name": handle + " Name"}, "is_blue_verified": True}}},
         "legacy": {"full_text": text, "created_at": "Wed Oct 28 09:15:00 +0000 2026", "favorite_count": likes, "retweet_count": 1, "conversation_id_str": conv or rest_id, "in_reply_to_status_id_str": reply_to,
                    "entities": {"urls": [{"url": "https://t.co/abc", "expanded_url": "https://example.com/post"}]},
                    "extended_entities": {"media": [{"type": "photo", "media_url_https": "https://pbs.twimg.com/a.jpg"}]}}, "views": {"count": "1200"}}
    if quoted:
        t["quoted_status_result"] = {"result": quoted}
    if note:
        t["note_tweet"] = {"note_tweet_results": {"result": {"text": note}}}
    return t


X_BODY = {"data": {"threaded_conversation_with_injections_v2": {"instructions": [{"entries": [
    {"content": {"itemContent": {"tweet_results": {"result": gql_tweet("100", "Root $NVDA setup see https://t.co/abc", quoted=gql_tweet("90", "Quoted idea about EPs", uid="9", handle="other"))}}}},
    {"content": {"items": [{"item": {"itemContent": {"tweet_results": {"result": {"tweet": gql_tweet("101", "2/ stop under the low", conv="100", reply_to="100")}}}}}]}},
    {"content": {"itemContent": {"tweet_results": {"result": gql_tweet("102", "nice thread", uid="2", handle="fan", conv="100", reply_to="100", likes=40)}}}},
    {"content": {"itemContent": {"tweet_results": {"result": gql_tweet("103", "meh", uid="3", handle="troll", conv="100", reply_to="100", likes=1)}}}}]}]}}}


def test_x_graphql_thread_build():
    from finsocnet.adapters import x
    tweets = x.collect_tweets([X_BODY])
    assert set(tweets) == {"100", "101", "102", "103", "90"} and tweets["100"]["text"] == "Root $NVDA setup see https://example.com/post"
    rec = valid(x.build_record("100", tweets, 100, None))
    kinds = [(s["locator"]["tweet_id"], s["kind"]) for s in rec["segments"]]
    assert kinds[:3] == [("100", "post"), ("101", "post"), ("102", "reply")] and rec["content_type"] == "thread" and rec["segments"][-1]["locator"].get("quoted_id") == "90"
    assert rec["author"]["handle"] == "@Qullamaggie" and "$NVDA" in rec["mentions"] and rec["media"][0]["kind"] == "image"
    capped = x.build_record("100", tweets, 1, None)
    assert len([s for s in capped["segments"] if s["kind"] == "reply" and "quoted_id" not in s["locator"]]) == 1
    with pytest.raises(CliError) as e:
        x.build_record("999", tweets, 10, None)
    assert e.value.code == "NOT_FOUND"
    assert x.tweet_id("https://x.com/Qullamaggie/status/1851234567890123456?s=20") == "1851234567890123456" and x.handle_of("https://x.com/Qullamaggie/") == "Qullamaggie"


def test_x_profile_parse_and_note_tweets():
    from finsocnet.adapters import x
    body = {"data": {"user": {"result": {"rest_id": "1", "is_blue_verified": True, "core": {"screen_name": "Qullamaggie", "name": "Kristjan"},
                                         "legacy": {"description": "Swing trader", "followers_count": 100000, "created_at": "Sat Mar 01 10:00:00 +0000 2015", "entities": {"url": {"urls": [{"expanded_url": "https://qullamaggie.com"}]}}}}}}}
    p = x.parse_profile([body], "qullamaggie")
    assert p["source_id"] == "x:user:qullamaggie" and p["followers"] == 100000 and p["links"] == ["https://qullamaggie.com"] and p["joined_at"] == "2015-03-01"
    t = x.parse_tweet(gql_tweet("5", "short", note="the full long-form note text"))
    assert t["text"] == "the full long-form note text"


def test_x_requires_a_logged_in_session(repo, conn, run_id, capsys):
    from finsocnet.adapters.x import X
    from finsocnet.core.platform import run_platform_cli
    with pytest.raises(SystemExit) as e:
        run_platform_cli(X(), argv=["fetch", "100"])
    out = json.loads(capsys.readouterr().out)
    assert e.value.code == 3 and out["error"]["code"] == "LOGIN_REQUIRED" and "session export" in out["error"]["hint"]


MEDIUM_RSS = """<?xml version="1.0"?><rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel><title>Stories by Dorian</title>
<item><title>What is data cleaning in trading</title><link>https://medium.com/@ztraderdorian/what-is-data-cleaning-in-trading-00f164ca71a0?source=rss</link><dc:creator>Dorian</dc:creator>
<pubDate>Mon, 20 Oct 2026 08:00:00 GMT</pubDate><category>trading</category><content:encoded><![CDATA[<p>Survivorship bias inflates backtests.</p>]]></content:encoded></item></channel></rss>"""


def test_medium_feed_and_article():
    from finsocnet.adapters import medium
    refs_ = medium.feed_refs(MEDIUM_RSS)
    assert refs_[0]["id"] == "medium:00f164ca71a0" and refs_[0]["author_handle"] == "Dorian" and refs_[0]["ref"].endswith("00f164ca71a0")
    assert medium.feed_url("@ztraderdorian") == ("https://medium.com/feed/@ztraderdorian", "medium:user:ztraderdorian")
    assert medium.feed_url("algorithmic-trading")[1] == "medium:tag:algorithmic-trading" and medium.feed_url("https://medium.com/tag/trading/")[0] == "https://medium.com/feed/tag/trading"
    html = ARTICLE_HTML.replace("<footer>", "<div>Member-only story</div><footer>")
    rec = valid(medium.article_record("https://medium.com/@ztraderdorian/what-is-data-cleaning-in-trading-00f164ca71a0", html, None))
    assert rec["id"] == "medium:00f164ca71a0" and rec["extra"]["member_only"] is True and rec["extra"]["truncated"] is True and rec["author"]["handle"] == "@ztraderdorian"


# --- real agent browser on a local page -----------------------------------------------------------------

def _chrome() -> bool:
    try:
        browser_proc.find_chrome()
        return True
    except CliError:
        return False


@pytest.mark.skipif(not _chrome(), reason="no Chrome/Chromium binary")
def test_web_fetch_with_the_real_agent_browser(repo, conn, tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(ARTICLE_HTML.replace("https://example.org/blog/trailing-stops/?utm_source=x", "http://127.0.0.1/local/trailing"))
    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    handler.log_message = lambda *a, **k: None  # type: ignore[attr-defined]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = 19600 + os.getpid() % 300
    monkeypatch.setenv("CDP_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("BROWSER_PROFILE_DIR", str(tmp_path / "profile"))
    (repo / "config" / "budgets.yaml").write_text("default: {per_minute: 100, per_hour: 1000, per_day: 10000, min_delay_ms: 1, max_delay_ms: 2}\n")
    from finsocnet.core import budgets
    budgets._load.cache_clear()
    try:
        browser_proc.start(headless=True)
        from finsocnet.adapters.web import Web
        rec = valid(Web().fetch(f"http://127.0.0.1:{srv.server_port}/index.html", wait="load"))
        assert rec["title"] == "Trailing stops explained" and "trail the 10-day" in " ".join(s["text"] for s in rec["segments"]) and rec["id"].startswith("web:")
        assert Web().discover(f"http://127.0.0.1:{srv.server_port}/index.html")
    finally:
        browser_proc.stop()
        srv.shutdown()
        budgets._load.cache_clear()

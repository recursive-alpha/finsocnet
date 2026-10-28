"""Fixture tests for adapters that talk to public JSON APIs (recorded responses in tests/fixtures/<platform>/)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from finsocnet.core import http
from finsocnet.core.records import schema_errors
from tests.integration.test_kb_content import kb

FX = Path(__file__).resolve().parents[1] / "fixtures"


def fixture(platform: str, name: str) -> bytes:
    return (FX / platform / name).read_bytes()


class Router:
    """Mock transport: maps URL substrings to fixture files / bytes."""

    def __init__(self, routes: dict[str, bytes | tuple[int, bytes]]):
        self.routes, self.calls = routes, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        for frag, body in self.routes.items():
            if frag in url:
                code, content = body if isinstance(body, tuple) else (200, body)
                return httpx.Response(code, content=content, headers={"content-type": "application/json"})
        return httpx.Response(404, content=b"{}")


@pytest.fixture
def mock_http(repo):
    def install(routes):
        r = Router(routes)
        http.set_transport(httpx.MockTransport(r))
        return r
    yield install
    http.set_transport(None)


def valid(rec):
    assert schema_errors("content_record", rec) == []
    assert [s["seq"] for s in rec["segments"]] == list(range(len(rec["segments"])))
    return rec


def test_hackernews(mock_http):
    from finsocnet.adapters import hackernews as hn
    mock_http({"/search?": fixture("hackernews", "search.json"), "/items/8863": fixture("hackernews", "item.json")})
    items = hn.HackerNews().search("momentum trading", limit=3)
    assert items and items[0]["id"].startswith("hn:") and items[0]["ref"].startswith("https://news.ycombinator.com/item?id=")
    rec = valid(hn.HackerNews().fetch("https://news.ycombinator.com/item?id=8863"))
    assert rec["id"] == "hn:8863" and rec["segments"][0]["kind"] == "post" and rec["content_type"] == "thread"
    assert any(s["kind"] == "comment" and s["locator"]["parent_id"] and s["author"]["handle"] for s in rec["segments"])
    with pytest.raises(Exception):
        hn.HackerNews().fetch("not an id")


def test_stackexchange(mock_http):
    from finsocnet.adapters import stackexchange as se
    qid = json.loads(fixture("stackexchange", "search.json"))["items"][0]["question_id"]
    mock_http({f"/questions/{qid}/answers": fixture("stackexchange", "answers.json"), f"/questions/{qid}": fixture("stackexchange", "question.json"),
               "/search/advanced": fixture("stackexchange", "search.json"), "/users/2114": fixture("stackexchange", "user.json")})
    items = se.StackExchange().search("momentum", limit=2, site="quant")
    assert items[0]["id"] == f"stackexchange:quant:{qid}" and items[0]["kind"] == "question" and items[0]["metrics"]["score"] is not None
    rec = valid(se.StackExchange().fetch(f"https://quant.stackexchange.com/questions/{qid}/slug"))
    kinds = [s["kind"] for s in rec["segments"]]
    assert rec["id"] == f"stackexchange:quant:{qid}" and kinds[0] == "question" and "answer" in kinds
    ans = next(s for s in rec["segments"] if s["kind"] == "answer")
    assert {"post_id", "score", "accepted"} <= set(ans["locator"]) and ans["author"]["handle"]
    assert se.parse_ref("stackexchange:money:42", "quant") == ("money", "42") and se.parse_ref("7", "quant") == ("quant", "7")
    assert se.StackExchange().profile("2114", site="quant")["source_id"] == "stackexchange:user:quant:2114"


def test_stackexchange_code_blocks_become_code_segments():
    from finsocnet.adapters import stackexchange as se
    segs = se.body_segments("<p>Use this:</p><pre><code>import pandas as pd\nprint(1)</code></pre><p>Done.</p>", {"post_id": 5}, "answer", 3)
    assert [s["kind"] for s in segs] == ["answer", "code"] and segs[1]["text"].startswith("import pandas") and segs[0]["seq"] == 3 and segs[1]["seq"] == 4


def test_stackexchange_backoff_and_quota(mock_http, monkeypatch):
    from finsocnet.adapters import stackexchange as se
    from finsocnet.core.output import CliError
    mock_http({"/search/advanced": json.dumps({"items": [], "quota_remaining": 3}).encode()})
    with pytest.raises(CliError) as e:
        se.StackExchange().search("x")
    assert e.value.code == "RATE_LIMITED"


def test_bluesky(mock_http):
    from finsocnet.adapters import bluesky as bs
    mock_http({"getPostThread": fixture("bluesky", "thread.json"), "getAuthorFeed": fixture("bluesky", "feed.json"), "getProfile": fixture("bluesky", "profile.json"),
               "searchPosts": fixture("bluesky", "search.json")})
    prof = bs.Bluesky().profile("bsky.app")
    assert prof["source_id"] == "bluesky:user:bsky.app" and prof["followers"] and prof["platform"] == "bluesky"
    lst = bs.Bluesky().list("@bsky.app", limit=3)
    assert lst["items"] and lst["items"][0]["id"].startswith("bluesky:did:plc:") and lst["source"]["id"] == "bluesky:user:bsky.app"
    uri = json.loads(fixture("bluesky", "thread.json"))["thread"]["post"]["uri"]
    rec = valid(bs.Bluesky().fetch(uri))
    assert rec["id"].startswith("bluesky:did:plc:") and rec["segments"][0]["kind"] == "post" and rec["segments"][0]["author"]["handle"]
    assert bs.parse_ref("https://bsky.app/profile/bsky.app/post/3abc") == "at://bsky.app/app.bsky.feed.post/3abc"


def test_github(mock_http):
    from finsocnet.adapters import github as gh
    mock_http({"/readme": fixture("github", "readme.json"), "/git/trees/main": fixture("github", "tree.json"), "/search/repositories": fixture("github", "search.json"),
               "/repos/psf/requests": fixture("github", "repo.json"), "/users/psf": fixture("github", "user.json")})
    s = gh.GitHub().search("algorithmic trading backtest", limit=2)
    assert s[0]["id"].startswith("github:") and s[0]["metrics"]["stars"]
    rec = valid(gh.GitHub().fetch("psf/requests"))
    assert rec["id"] == "github:psf/requests" and rec["content_type"] == "repo" and rec["segments"][0]["kind"] == "paragraph"
    tree = gh.GitHub().tree("psf/requests", branch="main")
    assert any(f["readable"] for f in tree["files"]) and tree["repo"] == "psf/requests"
    assert gh.parse_ref("https://github.com/o/r/blob/main/a/b.py") == ("o", "r", "a/b.py") and gh.parse_ref("o/r:x.py") == ("o", "r", "x.py")
    f = gh.file_record({"full_name": "o/r", "owner": {"login": "o"}, "html_url": "https://github.com/o/r", "default_branch": "main"}, "s.py", "\n".join(f"x{i}=1" for i in range(130)), "abcdef1234", None)
    assert f["id"] == "github:o/r:s.py@abcdef1" and [s["locator"]["line_start"] for s in f["segments"]] == [1, 61, 121] and valid(f)


def test_research_openalex(mock_http):
    from finsocnet.adapters import research as rs
    mock_http({"/works/doi:10.1111/1540-6261.00502": fixture("research", "openalex_search.json").replace(b'"results"', b'"results"'), "/works": fixture("research", "openalex_search.json")})
    items = rs.Research().search("momentum trading", limit=2)
    assert items[0]["id"].startswith(("paper:doi:", "paper:openalex:", "arxiv:")) and items[0]["title"]
    w = json.loads(fixture("research", "openalex_search.json"))["results"][0]
    assert rs.abstract_of(w).startswith("This") or len(rs.abstract_of(w)) > 50
    rec = valid(rs.build_record(w, None))
    assert rec["content_type"] == "paper" and rec["segments"][0]["kind"] == "paragraph" and rec["extra"]["authors"]


def test_research_s2_and_id_rules(mock_http):
    from finsocnet.adapters import research as rs
    mock_http({"/paper/search": json.dumps({"data": [{"paperId": "abc", "title": "T", "abstract": "A" * 20, "year": 2020, "authors": [{"name": "X"}], "externalIds": {"ArXiv": "2401.01234"}}]}).encode()})
    assert rs.Research().search("q", provider="s2")[0]["id"] == "arxiv:2401.01234"
    assert rs.paper_id({"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/ABC", "ids": {}}) == "paper:doi:10.1/abc"
    assert rs.paper_id({"id": "https://openalex.org/W1", "doi": None, "ids": {}}) == "paper:openalex:W1"


def test_papers_hf_and_arxiv(mock_http):
    from finsocnet.adapters import papers as pp
    hf = json.loads(fixture("paper", "hf_search.json"))
    hf[0]["paper"]["githubRepo"] = "https://github.com/x/y"
    mock_http({"/papers/search": json.dumps(hf).encode(), "/daily_papers": fixture("paper", "hf_daily.json"), "/api/query": fixture("paper", "arxiv.xml"), "/papers/2401.01234": json.dumps({"githubRepo": "https://github.com/example/momentum-vol"}).encode()})
    assert pp.Papers().search("trading", has_code=True)[0]["metrics"]["github_repo"] == "https://github.com/x/y"
    assert len(pp.Papers().search("trading")) == 2 and pp.Papers().trending(limit=2)
    rec = valid(pp.Papers().fetch("https://arxiv.org/abs/2401.01234v2", pdf=True))
    assert rec["id"] == "arxiv:2401.01234" and rec["extra"]["version"] == "v2" and "https://github.com/example/momentum-vol" in rec["links"] and "document.py fetch" in rec["extra"]["pdf_download_hint"]
    assert pp.arxiv_id("arxiv:2401.01234") == ("2401.01234", None)


def test_podcast(mock_http):
    from finsocnet.adapters import podcast as pc
    feed = "https://feeds.megaphone.fm/CWT9205947236"
    mock_http({"/search": fixture("podcast", "search.json"), "megaphone.fm": fixture("podcast", "feed.xml")})
    shows = pc.Podcast().search("chat with traders", limit=2)
    assert shows[0]["kind"] == "show" and shows[0]["id"] == f"podcast:feed:{pc.feed_key(shows[0]['ref'])}"
    lst = pc.Podcast().list(feed, limit=3)
    assert len(lst["items"]) == 3 and lst["next_cursor"] and lst["source"]["id"].startswith("podcast:feed:")
    ep = pc.Podcast().fetch(f"{feed}#{lst['next_cursor']}")
    valid(ep)
    assert ep["content_type"] == "episode" and ep["extra"]["needs_audio"] is True and ep["media"][0]["kind"] == "audio"
    assert pc.guests_hint("Defense First with Example Guest", "") == ["Example Guest"] and pc.guests_hint("Ep 4 ft. Jane Doe and more") == ["Jane Doe"]


def test_podcast_transcripts_vtt_and_json():
    from finsocnet.adapters import podcast as pc
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello and welcome.\n\n00:00:05.500 --> 00:00:09.000\nToday we talk <v Guest>risk</v>.\n"
    e = pc.parse_vtt_srt(vtt)
    assert e == [{"start": 1.0, "end": 5.0, "text": "Hello and welcome."}, {"start": 5.5, "end": 9.0, "text": "Today we talk risk."}]
    srt = "1\n00:01:02,000 --> 00:01:04,500\nLine one\n\n"
    assert pc.parse_vtt_srt(srt)[0]["start"] == 62.0
    assert pc.parse_json_transcript(json.dumps({"segments": [{"startTime": 0, "endTime": 2, "body": "Hi"}]}))[0]["text"] == "Hi"


def test_rss_list_fetch_discover(mock_http):
    from finsocnet.adapters import rss
    feed = "https://www.federalreserve.gov/feeds/press_monetary.xml"
    mock_http({"press_monetary.xml": fixture("rss", "feed.xml"), "federalreserve.gov/": b"<html><head><link rel='alternate' type='application/rss+xml' href='/feeds/press_all.xml' title='All'></head></html>"})
    lst = rss.RSS().list(feed, limit=5)
    assert len(lst["items"]) == 2 and lst["items"][0]["id"].startswith("web:") and lst["source"]["id"].startswith("rss:feed:")
    nothing_new = rss.RSS().list(feed, cursor=lst["next_cursor"])
    assert nothing_new["items"] == []
    found = rss.discover_feeds("<link rel='alternate' type='application/atom+xml' href='/a.xml'>", "https://x.org/blog/")
    assert found[0]["href"] == "https://x.org/a.xml"


def test_rss_entry_with_full_content_becomes_a_record():
    from finsocnet.adapters import rss
    import feedparser
    xml = """<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0"><channel><title>Blog</title><item><title>Trail stops</title><link>https://b.org/p/1</link>
    <guid>g1</guid><pubDate>Tue, 28 Oct 2026 10:00:00 GMT</pubDate><content:encoded><![CDATA[<p>%s</p><p>Second paragraph with $SPY and https://example.com/x</p>]]></content:encoded></item></channel></rss>""" % ("word " * 120)
    src, items = rss.feed_items(xml, "https://b.org/feed")
    rec = valid(rss.entry_record(items[0]["entry"], "https://b.org/feed", src))
    assert rec["id"] == items[0]["ref"]["id"] and rec["platform"] == "web" and "$SPY" in rec["mentions"] and rec["published_at"] == "2026-10-28T10:00:00Z"


def test_sec(mock_http, monkeypatch):
    from finsocnet.adapters import sec
    from finsocnet.core.output import CliError
    mock_http({"submissions/CIK0001067983.json": fixture("sec", "submissions.json")})
    with pytest.raises(CliError) as e:
        sec.SEC().profile("1067983")
    assert e.value.code == "USAGE" and "SEC_USER_AGENT" in e.value.message
    monkeypatch.setenv("SEC_USER_AGENT", "FinSocNet test@example.com")
    assert sec.SEC().profile("1067983")["source_id"] == "sec:cik:0001067983"
    lst = sec.SEC().list("1067983", limit=3)
    assert lst["items"][0]["id"].startswith("sec:") and lst["source"]["id"] == "sec:cik:0001067983"
    assert sec.SEC().list("1067983", forms="4")["items"] and all(i["metrics"]["form"] == "4" for i in sec.SEC().list("1067983", forms="4")["items"])
    table = """<informationTable><infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><titleOfClass>COM</titleOfClass><value>1000</value><shrsOrPrnAmt><sshPrnamt>50</sshPrnamt></shrsOrPrnAmt></infoTable>
    <infoTable><nameOfIssuer>AMEX</nameOfIssuer><titleOfClass>COM</titleOfClass><value>5000</value><shrsOrPrnAmt><sshPrnamt>70</sshPrnamt></shrsOrPrnAmt></infoTable></informationTable>"""
    h = sec.parse_information_table(table)
    assert [x["issuer"] for x in h] == ["AMEX", "APPLE INC"]
    rec = valid(sec.build_record("0001067983", "BRK", {"accession": "0000950123-25-003211", "form": "13F-HR", "date": "2025-02-14", "primary": "p.htm", "description": ""}, "<p>Filing text paragraph one is long enough to be kept. " * 3 + "</p>", None, h))
    assert any("13F holding 1: AMEX" in s["text"] for s in rec["segments"]) and rec["extra"]["evidence_level_hint"] == "audited"


def test_telegram_preview_parser(mock_http):
    from finsocnet.adapters import telegram as tg
    html = fixture("telegram", "channel.html").decode()
    p = tg.parse_channel(html)
    assert len(p["messages"]) == 20 and p["info"]["title"].startswith("Pavel Durov") and p["info"]["more"].startswith("/s/durov?before=")
    mock_http({"t.me/s/durov": html.encode()})
    prof = tg.Telegram().profile("https://t.me/durov")
    assert prof["source_id"] == "telegram:channel:durov" and prof["followers"] == "10.2M"
    lst = tg.Telegram().list("durov", limit=5)
    assert len(lst["items"]) == 5 and lst["items"][0]["id"].startswith("telegram:durov:") and lst["next_cursor"]
    mid = p["messages"][3]["id"]
    rec = valid(tg.Telegram().fetch(f"https://t.me/durov/{mid}"))
    assert rec["id"] == f"telegram:durov:{mid}" and rec["segments"][0]["locator"] == {"msg_id": mid}
    assert tg.channel_name("https://t.me/s/durov") == "durov" and tg.channel_name("@durov") == "durov"


def test_substack(mock_http):
    from finsocnet.adapters import substack as sb
    arch = json.loads(fixture("substack", "archive.json"))
    post = json.loads(fixture("substack", "post.json"))
    mock_http({"/api/v1/archive": fixture("substack", "archive.json"), f"/api/v1/posts/{post['slug']}": fixture("substack", "post.json"), f"/post/{post['id']}/comments": fixture("substack", "comments.json")})
    lst = sb.Substack().list("https://www.noahpinion.blog", limit=2)
    assert lst["items"][0]["id"].startswith("substack:www-noahpinion-blog:") and lst["source"]["id"] == "substack:publication:www-noahpinion-blog"
    rec = valid(sb.Substack().fetch(f"https://www.noahpinion.blog/p/{post['slug']}"))
    kinds = {s["kind"] for s in rec["segments"]}
    assert rec["content_type"] == "article" and "paragraph" in kinds and "comment" in kinds and rec["extra"]["audience"] == "everyone" and rec["extra"]["truncated"] is False
    assert sb.pub_base("macro") == "https://macro.substack.com" and sb.subdomain("https://macro.substack.com") == "macro"
    paid = sb.build_record("https://x.substack.com", "x", {**post, "audience": "only_paid", "body_html": "<p>teaser</p>"}, [], None)
    assert paid["extra"]["truncated"] is True


def test_web_search_backend_failure_is_rate_limited(monkeypatch):
    import sys, types
    from finsocnet.adapters import web_search as ws
    from finsocnet.core.output import CliError

    class Boom:
        def text(self, *a, **k):
            raise RuntimeError("DNSError: no records")

    monkeypatch.setitem(sys.modules, "ddgs", types.SimpleNamespace(DDGS=Boom))
    monkeypatch.setattr(ws.time, "sleep", lambda s: None)
    with pytest.raises(CliError) as e:
        ws.WebSearch().search("kelly")
    assert e.value.code == "RATE_LIMITED" and e.value.retry_after_sec == 120


def test_stackexchange_tag_url_lists_and_dispatches(monkeypatch):
    from finsocnet.adapters import stackexchange as se
    from finsocnet.core import dispatch

    assert dispatch.classify("https://quant.stackexchange.com/questions/tagged/risk-management")["action"] == "list"
    assert dispatch.classify("https://quant.stackexchange.com/questions/1234/some-title")["action"] == "fetch"
    seen = {}

    def fake_get(self, path, site, **params):
        seen.update(path=path, site=site, params=params)
        return {"items": [], "has_more": False}

    monkeypatch.setattr(se.StackExchange, "_get", fake_get)
    res = se.StackExchange().list("https://quant.stackexchange.com/questions/tagged/risk-management")
    assert seen["site"] == "quant" and seen["params"]["tagged"] == "risk-management" and res["source"]["id"] == "stackexchange:tag:quant:risk-management"


def test_profile_avatar_extractors():
    from finsocnet.adapters import reddit, telegram, youtube
    thumbs = [{"id": "0", "url": "https://yt/banner.jpg", "width": 1060, "height": 175}, {"id": "avatar_uncropped", "url": "https://yt/avatar.jpg"}]
    assert youtube.channel_avatar(thumbs) == "https://yt/avatar.jpg"
    assert youtube.channel_avatar([{"url": "https://yt/a.jpg", "width": 88, "height": 88}, {"url": "https://yt/b.jpg", "width": 176, "height": 176}]) == "https://yt/b.jpg"
    assert youtube.channel_avatar([{"url": "https://yt/wide.jpg", "width": 1060, "height": 175}]) is None
    assert reddit._icon({"icon_img": "https://styles.redditmedia.com/t5_2/a.png?width=256&amp;s=abc", "community_icon": ""}) == "https://styles.redditmedia.com/t5_2/a.png"
    assert reddit._icon({"snoovatar_img": "https://i.redd.it/snoovatar/avatars/x.png"}) == "https://i.redd.it/snoovatar/avatars/x.png" and reddit._icon({}) is None
    page = '<div class="tgme_channel_info_header"><i class="tgme_page_photo_image"><img src="https://cdn4.telesco.pe/file/x.jpg"></i><div class="tgme_channel_info_header_title">T</div></div>'
    assert telegram.parse_channel(page)["info"]["photo"] == "https://cdn4.telesco.pe/file/x.jpg"


def test_youtube_channel_ids_are_not_treated_as_handles():
    from finsocnet.adapters import youtube
    assert youtube.channel_url("UCLn8btkaQ5hVWNMt9TxQtsQ") == "https://www.youtube.com/channel/UCLn8btkaQ5hVWNMt9TxQtsQ"
    assert youtube.channel_url("@qullamaggie") == "https://www.youtube.com/@qullamaggie" and youtube.channel_url("qullamaggie") == "https://www.youtube.com/@qullamaggie"
    assert youtube.channel_url("UCsomething") == "https://www.youtube.com/@UCsomething"  # too short for an id
    assert youtube.channel_url("https://www.youtube.com/@x/videos") == "https://www.youtube.com/@x/videos"


def test_youtube_bot_check_is_a_checkpoint_not_an_internal_error(monkeypatch):
    from finsocnet.adapters import youtube
    from finsocnet.core.output import CliError

    class Boom:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, *a, **k):
            raise RuntimeError("ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies")
    monkeypatch.setattr(youtube, "_ydl", lambda *a, **k: Boom())
    with pytest.raises(CliError) as e:
        youtube.YouTube().fetch("dQw4w9WgXcQ")
    assert e.value.code == "CHECKPOINT" and "session" in e.value.hint

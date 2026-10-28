"""The standard adapter CLI (specs/05 §1.2): known flags, --ingest, --enqueue, --save-cursor, UNSUPPORTED, session guard, v1 wrappers."""

from __future__ import annotations

import json

import pytest

from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, run_platform_cli
from finsocnet.core.queue import list_items


class Fake(PlatformAdapter):
    platform = "reddit"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--sort",), {"default": "top"})]}

    def search(self, query, *, limit=20, since=None, sort="top", **_):
        return [item_ref("https://r/1", "reddit:aaa111", "thread", f"{query} {sort}"), item_ref("https://r/2", "reddit:bbb222", "thread", "new one")][:limit]

    def profile(self, target, **_):
        return profile_record("reddit", "reddit:user:example", "u/example", display_name="Example")

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        return list_result([item_ref("https://r/1", "reddit:aaa111", "thread", "t"), item_ref("https://r/2", "reddit:bbb222", "thread", "u")], "CUR2", {"id": "reddit:subreddit:test"})

    def fetch(self, item, **_):
        return content_record("reddit:aaa111", "reddit", "thread", [{"seq": 0, "kind": "post", "locator": {"comment_id": "t3_aaa111"}, "text": "A post about sizing after losses"}],
                              title="T", source={"id": "reddit:subreddit:test", "kind": "subreddit", "title": "r/test"})


class OnlyFetch(PlatformAdapter):
    platform = "web"
    capabilities = frozenset({"fetch"})


def call(adapter, capsys, *argv):
    code = 0
    try:
        run_platform_cli(adapter, argv=list(argv))
    except SystemExit as e:
        code = int(e.code or 0)
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    return code, json.loads(out[0])


def test_search_marks_known_and_passes_platform_options(conn, run_id, reddit, capsys):
    from finsocnet.core import content
    content.add_content(conn, reddit(), run_id)  # reddit:1xg9xq1 exists, aaa111 does not
    conn.execute("INSERT INTO sources (id, platform, kind) VALUES ('reddit:subreddit:test', 'reddit', 'subreddit')")
    code, env = call(Fake(), capsys, "search", "sizing", "--sort", "new")
    assert code == 0 and env["data"]["count"] == 2 and env["data"]["items"][0]["title"] == "sizing new" and [i["known"] for i in env["data"]["items"]] == [False, False]
    code, env = call(Fake(), capsys, "fetch", "aaa111", "--ingest", "--run", str(run_id))
    assert code == 0 and env["data"]["ingest"]["status"] == "created" and env["data"]["content"]["segments"] == 1 and env["data"]["content"]["record_path"].startswith("data/records/reddit/")
    code, env = call(Fake(), capsys, "search", "sizing")
    assert [i["known"] for i in env["data"]["items"]] == [True, False]


def test_list_enqueue_and_save_cursor_and_write_needs_run(conn, run_id, capsys):
    code, env = call(Fake(), capsys, "list", "r/test", "--enqueue", "--save-cursor", "--run", str(run_id))
    assert code == 0 and env["data"]["next_cursor"] == "CUR2" and len(env["data"]["enqueued"]) == 2
    assert conn.execute("SELECT crawl_cursor FROM sources WHERE id = 'reddit:subreddit:test'").fetchone()[0] == "CUR2"
    q = list_items(conn)
    assert {i["target"] for i in q} == {"https://r/1", "https://r/2"} and all(i["origin"] == "source_refresh" and i["platform"] == "reddit" for i in q)
    code, env = call(Fake(), capsys, "list", "r/test", "--enqueue")
    assert code == 2 and env["error"]["code"] == "RUN_REQUIRED"


def test_profile_ingest_creates_source_and_lists_person_candidates(conn, run_id, capsys):
    conn.execute("INSERT INTO persons (id, canonical_name) VALUES ('example-person', 'Example Person')")
    conn.execute("INSERT INTO person_aliases (alias_key, alias, platform, person_id) VALUES ('example', 'u/example', 'reddit', 'example-person')")
    code, env = call(Fake(), capsys, "profile", "u/example", "--ingest", "--run", str(run_id))
    assert code == 0 and env["data"]["ingest"]["status"] == "created" and env["data"]["person_candidates"][0]["person"]["id"] == "example-person"
    assert env["data"]["profile"]["known_person_id"] == "example-person"
    assert conn.execute("SELECT title FROM sources WHERE id = 'reddit:user:example'").fetchone()[0] == "Example"


def test_unsupported_subcommand_exits_2(repo, capsys):
    code, env = call(OnlyFetch(), capsys, "search", "x")
    assert code == 2 and env["error"]["code"] == "UNSUPPORTED" and "fetch" in env["error"]["hint"]
    code, env = call(OnlyFetch(), capsys, "bogus")
    assert code == 2 and env["error"]["code"] == "USAGE"


def test_session_platforms_require_a_logged_in_session(conn, capsys):
    class NeedsLogin(Fake):
        platform = "x"
        requires_session = True
    code, env = call(NeedsLogin(), capsys, "search", "q")
    assert code == 3 and env["error"]["code"] == "LOGIN_REQUIRED"
    conn.execute("INSERT INTO browser_sessions (domain, platform, cookie_count, bundle_id, imported_at, login_state) VALUES ('x.com', 'x', 3, 'b', '2026-10-28T00:00:00Z', 'logged_in')")
    code, env = call(NeedsLogin(), capsys, "search", "q")
    assert code == 0


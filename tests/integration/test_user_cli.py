import json

import pytest

from finsocnet.core import dispatch, persons, queue, runs
from finsocnet.core.user_cli import explore_main, feedback_main, persons_main
from tests.conftest import make_card, make_decision
from tests.integration.test_cards import commit


def run(capsys, fn, *argv):
    code = 0
    try:
        fn(list(argv))
    except SystemExit as e:
        code = int(e.code or 0)
    return code, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.mark.parametrize("target,platform,action,kind", [
    ("https://www.youtube.com/watch?v=B1ALxAVtFfI", "youtube", "fetch", "url"), ("https://www.youtube.com/@Qullamaggie", "youtube", "profile", "url"),
    ("https://x.com/Qullamaggie/status/185", "x", "fetch", "url"), ("https://x.com/Qullamaggie", "x", "profile", "url"),
    ("https://www.reddit.com/r/Daytrading/comments/abc123/x/", "reddit", "fetch", "url"), ("https://medium.com/@z/post-title-00f164ca71a0", "medium", "fetch", "url"),
    ("https://noah.substack.com/p/hello", "substack", "fetch", "url"), ("https://arxiv.org/abs/2401.01234", "arxiv", "fetch", "url"), ("https://github.com/o/r", "github", "fetch", "url"),
    ("https://example.com/book.pdf", "file", "fetch", "url"), ("https://example.com/some/page", "web", "fetch", "url"), ("@qullamaggie", "", "profile", "handle"),
    ("how to size positions", "", "search", "query"), ("https://news.ycombinator.com/item?id=1", "hackernews", "fetch", "url"), ("https://t.me/durov", "telegram", "list", "url"),
])
def test_dispatch_rules(repo, target, platform, action, kind):
    c = dispatch.classify(target)
    assert (c["platform"], c["action"], c["target_kind"]) == (platform, action, kind)


def test_known_person_and_forum_hosts(repo):
    assert dispatch.classify("lance-breitstein", {"lance-breitstein"})["target_kind"] == "person"
    assert dispatch.classify("https://forums.babypips.com/t/x/1")["platform"] == "forum"


def test_explore_add_queues_with_origin_user(conn, run_id, capsys):
    conn.close()
    code, env = run(capsys, explore_main, "add", "https://x.com/Qullamaggie", "--priority", "0.9")
    assert code == 0 and env["data"]["status"] == "created" and env["data"]["classified_as"]["skill"] == "x-explorer"
    code, env = run(capsys, explore_main, "add", "https://x.com/Qullamaggie")
    assert env["data"]["status"] == "existing"
    code, env = run(capsys, explore_main, "show")
    assert env["data"]["items"][0]["origin"] == "user" and env["data"]["items"][0]["priority"] == 0.9


def test_persons_review_confirm_reject_reassign(seeded, run_id, capsys):
    persons.upsert(seeded, {"id": "example-owner", "canonical_name": "Example Owner"}, run_id)
    commit(seeded, run_id, make_decision())
    a = persons.add_appearance(seeded, {"person_id": "example-swing-trader", "content_id": "youtube:abc123def45", "role": "guest", "match_confidence": 0.5}, run_id)["appearance_id"]
    seeded.close()
    code, env = run(capsys, persons_main, "review", "--list")
    assert env["data"]["needs_review"][0]["appearance_id"] == a
    code, env = run(capsys, persons_main, "review", "--reassign", str(a), "--to", "example-owner")
    assert code == 0
    from finsocnet.core.db import connect
    c = connect()
    assert c.execute("SELECT match_status FROM person_appearances WHERE id = ?", (a,)).fetchone()[0] == "rejected"
    assert c.execute("SELECT person_id FROM card_citations WHERE id = 1").fetchone()[0] == "example-owner"
    assert c.execute("SELECT match_status FROM person_appearances WHERE person_id = 'example-owner' AND role = 'guest'").fetchone()[0] == "confirmed"
    c.close()
    code, env = run(capsys, persons_main, "review", "--reject", "9999")
    assert code == 5


def test_feedback_cli(conn, capsys):
    conn.close()
    code, env = run(capsys, feedback_main, "card", "41", "-1", "wrong", "claim")
    assert code == 0 and env["data"]["feedback_id"] == 1
    code, env = run(capsys, feedback_main, "card", "41", "great")
    assert code == 2 and env["error"]["code"] == "USAGE"

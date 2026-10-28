"""Person avatars: download, validation by bytes, content-addressed storage, primary rules, source icons, merge (specs/12-person-images.md)."""

from __future__ import annotations

import io

import httpx
import pytest

from finsocnet.core import content, http, persons
from finsocnet.core.output import CliError


def png(color=(200, 30, 30), size=(64, 48)) -> bytes:
    import random
    from PIL import Image
    rnd = random.Random(sum(color))
    im = Image.new("RGB", size, color)
    im.putdata([tuple((c + rnd.randint(0, 40)) % 256 for c in color) for _ in range(size[0] * size[1])])  # noise: real avatars are not flat
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


@pytest.fixture
def web():
    routes = {"https://img.example/a.png": (200, "image/png", png()), "https://img.example/b.png": (200, "image/png", png((10, 200, 10))),
              "https://img.example/page.html": (200, "text/html", b"<html>nope</html>" * 20), "https://img.example/fake.png": (200, "image/png", b"not really an image" * 20)}

    def handler(req: httpx.Request) -> httpx.Response:
        code, ctype, body = routes.get(str(req.url), (404, "text/plain", b"x"))
        return httpx.Response(code, headers={"content-type": ctype}, content=body)

    http.set_transport(httpx.MockTransport(handler))
    yield routes
    http.set_transport(None)


@pytest.fixture
def person(conn, run_id):
    persons.upsert(conn, {"id": "example-owner", "canonical_name": "Example Owner"}, run_id)
    return "example-owner"


def test_download_stores_a_content_addressed_file_and_sets_the_primary_avatar(conn, run_id, repo, person, web):
    r = persons.image_add(conn, person, run_id, url="https://img.example/a.png", platform="x")
    assert r["new"] and r["primary"] and (r["width"], r["height"]) == (64, 48)
    assert (repo / r["path"]).read_bytes() == web["https://img.example/a.png"][2] and r["path"].startswith("data/media/persons/example-owner/")
    p = persons.get(conn, person)
    assert p["avatar_path"] == r["path"] and p["avatar_sha256"] == r["sha256"] and p["avatar_mime"] == "image/png" and len(p["images"]) == 1
    # the same picture again changes nothing; a second picture does not steal the primary slot
    assert persons.image_add(conn, person, run_id, url="https://img.example/a.png")["new"] is False
    r2 = persons.image_add(conn, person, run_id, url="https://img.example/b.png", platform="youtube")
    assert r2["new"] and not r2["primary"] and persons.get(conn, person)["avatar_path"] == r["path"]
    assert persons.image_add(conn, person, run_id, url="https://img.example/b.png", primary=True)["primary"]
    assert persons.get(conn, person)["avatar_path"] == r2["path"]


def test_only_real_images_are_accepted(conn, run_id, person, web):
    for url in ("https://img.example/page.html", "https://img.example/fake.png"):
        with pytest.raises(CliError) as e:
            persons.image_add(conn, person, run_id, url=url)
        assert e.value.code == "VALIDATION_ERROR"
    with pytest.raises(CliError) as e:
        persons.image_add(conn, person, run_id, url="https://img.example/missing.png")
    assert e.value.code == "NOT_FOUND"
    with pytest.raises(CliError):
        persons.image_add(conn, person, run_id)  # neither url nor file
    assert persons.image_list(conn, person) == []


def test_local_file(conn, run_id, person, tmp_path):
    f = tmp_path / "me.png"
    f.write_bytes(png())
    assert persons.image_add(conn, person, run_id, file=str(f), kind="photo")["kind"] == "photo"
    assert persons.get(conn, person)["avatar_path"] is None  # a photo is not an avatar


def test_fetch_uses_person_and_source_urls_and_reports_errors(conn, run_id, person, web):
    conn.execute("UPDATE persons SET avatar_url = 'https://img.example/a.png' WHERE id = ?", (person,))
    content.upsert_source(conn, {"id": "youtube:channel:UCexample0000000000000000", "title": "Example", "person_id": person, "avatar_url": "https://img.example/b.png"})
    content.upsert_source(conn, {"id": "x:user:example", "title": "x", "person_id": person, "avatar_url": "https://img.example/fake.png"})
    res = persons.image_fetch(conn, person, run_id)
    assert len(res["stored"]) == 2 and [e["url"] for e in res["errors"]] == ["https://img.example/fake.png"]
    assert persons.image_fetch(conn, person, run_id)["already_stored"] == 2
    assert persons.image_fetch(conn, "example-owner", run_id)["errors"][0]["code"] == "VALIDATION_ERROR"


def test_merge_moves_images_and_the_avatar(conn, run_id, person, web):
    persons.upsert(conn, {"id": "example-dup", "canonical_name": "Example Dup"}, run_id)
    persons.image_add(conn, "example-dup", run_id, url="https://img.example/b.png")
    persons.merge(conn, "example-dup", person, run_id)
    p = persons.get(conn, person)
    assert len(p["images"]) == 1 and p["avatar_path"]
    assert persons.image_list(conn, "example-dup")[0]["person_id"] == person  # resolve_id follows the merge


def test_persons_carry_profession_affiliation_and_external_ids(conn, run_id):
    from finsocnet.core import persons
    persons.upsert(conn, {"id": "jane-professor", "canonical_name": "Jane Professor", "profession": "academic", "affiliation": "Example University", "domains": "asset pricing, macro",
                          "relevance": "publishes on the equity premium", "external_ids": {"orcid": "0000-0000-0000-0001", "openalex": "A1"}}, run_id)
    persons.upsert(conn, {"id": "pat-pm", "canonical_name": "Pat PM", "profession": "portfolio_manager"}, run_id)
    got = persons.get(conn, "jane-professor")
    assert got["profession"] == "academic" and got["external_ids"] == {"orcid": "0000-0000-0000-0001", "openalex": "A1"} and got["affiliation"] == "Example University"
    assert [p["id"] for p in persons.list_persons(conn, profession="academic")] == ["jane-professor"]
    assert {p["id"] for p in persons.list_persons(conn)} == {"jane-professor", "pat-pm"}
    from finsocnet.core.output import CliError
    import pytest
    with pytest.raises(CliError):
        persons.upsert(conn, {"id": "bad-one", "canonical_name": "Bad One", "profession": "wizard"}, run_id)
    persons.upsert(conn, {"id": "jane-professor", "affiliation": "Other University", "canonical_name": "Jane Professor"}, run_id)  # update keeps the rest
    assert persons.get(conn, "jane-professor")["profession"] == "academic"

from finsocnet.core import ids, normalize


def test_clean_text():
    assert normalize.clean_text("a\r\nb\x00\n\n\n\nc ") == "a\nb\n\nc"


def test_hash_text_ignores_case_and_punctuation():
    assert normalize.hash_text("Hello,  World!") == normalize.hash_text("hello world")
    assert normalize.hash_text("hello world") != normalize.hash_text("hello there")


def test_quote_matching_tolerates_punctuation_and_case_not_words():
    text = "So what I do is, once it's up like 3, 4 days after the breakout I sell a third"
    assert normalize.quote_in("once its up like 3 4 days after the breakout", text)
    assert normalize.quote_in("ONCE IT'S UP LIKE 3, 4 DAYS", text)
    assert not normalize.quote_in("once it is up like 3 4 days", text)
    assert not normalize.quote_in("", text)


def test_quote_key_removes_diacritics():
    assert normalize.quote_key("cắt lỗ 7%") == "cat lo 7"
    assert normalize.quote_in("cat lo", "Mình cắt lỗ ngay")


def test_alias_key():
    assert normalize.alias_key("@Qullamaggie") == "qullamaggie"
    assert normalize.alias_key("u/Example_DT") == "example_dt"
    assert normalize.alias_key("  Kristjan   Kullamägi ") == "kristjan kullamagi"


def test_id_builders():
    assert ids.content_id("youtube", "B1ALxAVtFfI") == "youtube:B1ALxAVtFfI"
    assert ids.content_id("substack", "example", "139876543") == "substack:example:139876543"
    assert ids.source_id("x", "user", "qullamaggie") == "x:user:qullamaggie"
    assert ids.person_id("Kristjan Kullamägi") == "kristjan-kullamagi"
    assert ids.person_id("Tom Dante", {"tom-dante"}) == "tom-dante-2"
    assert ids.handle_person_id("reddit", "u_example") == "reddit-u-example"


def test_unknown_platform_rejected():
    import pytest
    with pytest.raises(ValueError):
        ids.content_id("myspace", "1")


def test_canonical_url():
    u = ids.canonical_url("HTTPS://Example.com/Path/?utm_source=x&a=1&fbclid=z#frag")
    assert u == "https://example.com/Path?a=1"
    assert ids.canonical_url("https://x.com/u/status/1?s=20") == "https://x.com/u/status/1"
    assert ids.canonical_url("https://example.com/") == "https://example.com/"
    assert ids.web_content_id("https://example.com/a/") == ids.web_content_id("https://EXAMPLE.com/a?utm_x=1")

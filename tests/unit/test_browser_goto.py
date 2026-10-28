import pytest

from finsocnet.core import browser
from finsocnet.core.output import CliError


class _Pg:
    def __init__(self, msg):
        self.msg = msg

    def goto(self, *a, **k):
        raise RuntimeError(self.msg)


@pytest.mark.parametrize("msg,code", [("Page.goto: net::ERR_NAME_NOT_RESOLVED at https://x/", "NOT_FOUND"), ("Page.goto: Timeout 30000ms exceeded", "BROWSER_UNAVAILABLE"), ("Target closed", "BROWSER_UNAVAILABLE")])
def test_goto_maps_navigation_errors(msg, code):
    with pytest.raises(CliError) as e:
        browser.goto(_Pg(msg), "web", "https://x/")
    assert e.value.code == code and e.value.hint

"""Against the real Lounge API. Needs network and a paired screen's id in
``YTLOUNGE_SCREEN_ID``; selected with ``pixi run test-device``.

Only ``refresh`` and ``connect`` run here: neither changes what the TV
shows. The screen id is the durable key, so a token is fetched from it
first and no stored token is needed.
"""

from __future__ import annotations

import os

import pytest

from ytlounge import Lounge, Screen

pytestmark = pytest.mark.device


@pytest.fixture
def screen() -> Screen:
    screen_id = os.environ.get("YTLOUNGE_SCREEN_ID")
    if not screen_id:
        pytest.skip("set YTLOUNGE_SCREEN_ID to a paired screen's id")
    return Screen(screen_id=screen_id, lounge_token="", expiration=0)


def test_refresh_then_connect(screen: Screen) -> None:
    with Lounge(name="ytlounge-test") as lounge:
        refreshed = lounge.refresh(screen)
        assert refreshed.lounge_token and not refreshed.is_expired()
        session = lounge.connect(refreshed)
    assert session.sid and session.gsessionid


def test_refresh_twice_keeps_the_first_token_valid(screen: Screen) -> None:
    """A refresh is not a revocation: a tool holding an older token must
    keep working after another tool refreshed."""
    with Lounge(name="ytlounge-test") as lounge:
        first = lounge.refresh(screen)
        second = lounge.refresh(screen)
        assert lounge.connect(first).sid
        assert lounge.connect(second).sid

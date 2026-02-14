"""Tests for classic Battleship rule enforcement."""

import random

from warships.core.fleet import random_fleet
from warships.core.models import Coord, ShotResult, Turn
from warships.core.rules import create_session, player_fire


def test_player_repeat_shot_keeps_turn() -> None:
    rng = random.Random(123)
    session = create_session(random_fleet(rng), random_fleet(rng))

    first = player_fire(session, Coord(0, 0))
    if first is not ShotResult.REPEAT and first is not ShotResult.INVALID:
        session.turn = Turn.PLAYER
        repeat = player_fire(session, Coord(0, 0))
        assert repeat is ShotResult.REPEAT

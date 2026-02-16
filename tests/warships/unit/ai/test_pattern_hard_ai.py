import random

from warships.game.ai.pattern_hard import PatternHardAI
from warships.game.core.models import Coord, ShotResult


def test_pattern_hard_ai_choose_hunt_then_target() -> None:
    ai = PatternHardAI(random.Random(1))
    first = ai.choose_shot()
    assert isinstance(first, Coord)
    ai.notify_result(first, ShotResult.HIT)
    second = ai.choose_shot()
    assert isinstance(second, Coord)


def test_pattern_hard_ai_sunk_removes_cluster() -> None:
    ai = PatternHardAI(random.Random(2))
    ai.notify_result(Coord(2, 2), ShotResult.HIT)
    ai.notify_result(Coord(2, 3), ShotResult.SUNK)
    # should recover to hunt mode without crashing
    shot = ai.choose_shot()
    assert isinstance(shot, Coord)

import random

from warships.game.ai.hunt_target import HuntTargetAI
from warships.game.core.models import Coord, ShotResult


def test_hunt_target_ai_choose_and_notify_hit_then_sunk() -> None:
    ai = HuntTargetAI(random.Random(1))
    first = ai.choose_shot()
    assert isinstance(first, Coord)
    ai.notify_result(first, ShotResult.HIT)
    second = ai.choose_shot()
    assert isinstance(second, Coord)
    ai.notify_result(second, ShotResult.SUNK)
    third = ai.choose_shot()
    assert isinstance(third, Coord)


def test_hunt_target_ai_orientation_narrowing() -> None:
    ai = HuntTargetAI(random.Random(2))
    ai.notify_result(Coord(5, 5), ShotResult.HIT)
    ai.notify_result(Coord(5, 6), ShotResult.HIT)
    # With two horizontal hits, queue should narrow to same row.
    shot = ai.choose_shot()
    assert shot.row == 5

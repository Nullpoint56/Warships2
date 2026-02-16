import random

from warships.game.ai.probability_target import ProbabilityTargetAI
from warships.game.core.models import Coord, ShotResult


def test_probability_ai_choose_and_notify_cycle() -> None:
    ai = ProbabilityTargetAI(random.Random(1))
    shot = ai.choose_shot()
    assert isinstance(shot, Coord)
    ai.notify_result(shot, ShotResult.MISS)
    next_shot = ai.choose_shot()
    assert isinstance(next_shot, Coord)


def test_probability_ai_hit_cluster_and_sunk_consumes_length() -> None:
    ai = ProbabilityTargetAI(random.Random(2))
    ai.notify_result(Coord(0, 0), ShotResult.HIT)
    ai.notify_result(Coord(0, 1), ShotResult.SUNK)
    shot = ai.choose_shot()
    assert isinstance(shot, Coord)

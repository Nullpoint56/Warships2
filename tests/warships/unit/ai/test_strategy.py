import random

from warships.game.ai.hunt_target import HuntTargetAI
from warships.game.ai.strategy import AIStrategy
from warships.game.core.models import Coord, ShotResult


def test_concrete_strategy_is_subclass_of_interface() -> None:
    ai = HuntTargetAI(random.Random(1))
    assert isinstance(ai, AIStrategy)
    shot = ai.choose_shot()
    assert isinstance(shot, Coord)
    ai.notify_result(shot, ShotResult.MISS)

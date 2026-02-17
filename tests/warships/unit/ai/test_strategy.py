import random

from engine.api.ai import DecisionContext
from warships.game.ai.hunt_target import HuntTargetAI
from warships.game.ai.strategy import AIStrategy
from warships.game.core.models import Coord, ShotResult


def test_concrete_strategy_is_subclass_of_interface() -> None:
    ai = HuntTargetAI(random.Random(1))
    assert isinstance(ai, AIStrategy)
    shot = ai.choose_shot()
    assert isinstance(shot, Coord)
    ai.notify_result(shot, ShotResult.MISS)


def test_strategy_decide_writes_shot_into_blackboard() -> None:
    ai = HuntTargetAI(random.Random(3))
    decision = ai.decide(
        DecisionContext(
            now_seconds=1.0,
            delta_seconds=0.016,
            blackboard=ai.blackboard,
            observations={},
        )
    )
    assert decision == AIStrategy.ACTION_FIRE
    shot = AIStrategy.take_decided_shot(ai.blackboard)
    assert isinstance(shot, Coord)

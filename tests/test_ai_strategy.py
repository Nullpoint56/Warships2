"""Tests for AI strategy behavior."""

import random

from warships.ai.hunt_target import HuntTargetAI
from warships.core.models import ShotResult


def test_ai_never_repeats_in_first_50_shots() -> None:
    ai = HuntTargetAI(random.Random(7))
    seen: set[tuple[int, int]] = set()
    for _ in range(50):
        shot = ai.choose_shot()
        key = (shot.row, shot.col)
        assert key not in seen
        seen.add(key)
        ai.notify_result(shot, ShotResult.MISS)

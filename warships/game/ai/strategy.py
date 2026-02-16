"""AI strategy interface and selection utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.api.ai import Agent, Blackboard, DecisionContext, create_blackboard
from warships.game.core.models import Coord, ShotResult


class AIStrategy(Agent, ABC):
    """Warships AI strategy contract backed by engine AI primitives."""

    ACTION_FIRE = "fire"
    _NEXT_SHOT_KEY = "warships.ai.next_shot"

    def __init__(self) -> None:
        self._blackboard = create_blackboard()

    @property
    def blackboard(self) -> Blackboard:
        return self._blackboard

    def decide(self, context: DecisionContext) -> str:
        """Expose strategy through the generic engine Agent contract."""
        context.blackboard.set(self._NEXT_SHOT_KEY, self.choose_shot())
        return self.ACTION_FIRE

    @classmethod
    def take_decided_shot(cls, blackboard: Blackboard) -> Coord:
        """Read and clear the pending shot from blackboard."""
        shot = blackboard.remove(cls._NEXT_SHOT_KEY)
        if not isinstance(shot, Coord):
            raise TypeError("expected Coord shot in AI blackboard")
        return shot

    @abstractmethod
    def choose_shot(self) -> Coord:
        """Return next coordinate to fire."""

    @abstractmethod
    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        """Update strategy state with shot result."""

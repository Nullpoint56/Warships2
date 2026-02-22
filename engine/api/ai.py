"""Public AI primitive API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class Blackboard(Protocol):
    """Shared AI context storage contract."""

    def set(self, key: str, value: "BlackboardValue") -> None:
        """Set a value for key."""

    def get(self, key: str) -> "BlackboardValue | None":
        """Get value for key if present."""

    def require(self, key: str) -> "BlackboardValue":
        """Get required value or raise KeyError."""

    def has(self, key: str) -> bool:
        """Return whether key exists."""

    def remove(self, key: str) -> "BlackboardValue | None":
        """Remove key and return previous value if present."""

    def snapshot(self) -> dict[str, "BlackboardValue"]:
        """Return a copy of current blackboard values."""


class BlackboardValue(Protocol):
    """Opaque AI blackboard value contract."""


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Agent decision context for one think tick."""

    now_seconds: float
    delta_seconds: float
    blackboard: Blackboard
    observations: dict[str, BlackboardValue]


class Agent(Protocol):
    """AI agent contract."""

    def decide(self, context: DecisionContext) -> str:
        """Return next action identifier."""


def create_blackboard() -> Blackboard:
    """Create default blackboard implementation."""
    from engine.ai.blackboard import RuntimeBlackboard

    return RuntimeBlackboard()


def create_functional_agent(
    decide_fn: Callable[[DecisionContext], str],
) -> Agent:
    """Create callable-backed agent implementation."""
    from engine.ai.agent import FunctionalAgent

    return FunctionalAgent(decide_fn=decide_fn)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize scores into probability distribution."""
    from engine.ai.utility import normalize_scores as _normalize_scores

    return _normalize_scores(scores)


def best_action(scores: dict[str, float]) -> str | None:
    """Select best action from score map."""
    from engine.ai.utility import best_action as _best_action

    return _best_action(scores)


def combine_weighted_scores(
    weighted_scores: tuple[tuple[dict[str, float], float], ...],
) -> dict[str, float]:
    """Combine weighted score maps."""
    from engine.ai.utility import combine_weighted_scores as _combine_weighted_scores

    return _combine_weighted_scores(weighted_scores)

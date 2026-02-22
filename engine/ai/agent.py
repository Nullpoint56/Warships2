"""Agent implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.api.ai import Agent, DecisionContext


@dataclass(frozen=True, slots=True)
class FunctionalAgent(Agent):
    """Callable-backed agent implementation."""

    decide_fn: Callable[[DecisionContext], str]

    def decide(self, context: DecisionContext) -> str:
        return self.decide_fn(context)

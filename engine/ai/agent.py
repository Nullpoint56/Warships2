"""Agent implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.api.ai import DecisionContext


@dataclass(frozen=True, slots=True)
class FunctionalAgent:
    """Callable-backed agent implementation."""

    decide_fn: Callable[[DecisionContext], str]

    def decide(self, context: DecisionContext) -> str:
        return self.decide_fn(context)

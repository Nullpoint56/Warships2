"""Gameplay state-store implementation."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from engine.api.gameplay import StateSnapshot


class RuntimeStateStore[TState]:
    """Default versioned state-store implementation."""

    def __init__(self, initial_state: TState) -> None:
        self._value = initial_state
        self._revision = 0

    def snapshot(self) -> StateSnapshot[TState]:
        """Return immutable snapshot copy."""
        return StateSnapshot(value=deepcopy(self._value), revision=self._revision)

    def get(self) -> TState:
        """Return deep-copied current state value."""
        return deepcopy(self._value)

    def peek(self) -> TState:
        """Return current state value by reference (read-only contract)."""
        return self._value

    def set(self, value: TState) -> StateSnapshot[TState]:
        """Replace state value and increment revision."""
        self._value = value
        self._revision += 1
        return self.snapshot()

    def update(self, mutator: Callable[[TState], TState]) -> StateSnapshot[TState]:
        """Apply pure mutator over state value."""
        current = deepcopy(self._value)
        self._value = mutator(current)
        self._revision += 1
        return self.snapshot()

    def revision(self) -> int:
        return self._revision

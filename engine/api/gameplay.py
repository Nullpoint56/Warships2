"""Public gameplay-loop API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from engine.api.context import RuntimeContext

TState = TypeVar("TState")


class GameplaySystem(Protocol):
    """Standard gameplay system lifecycle contract."""

    def start(self, context: RuntimeContext) -> None:
        """Initialize system resources."""

    def update(self, context: RuntimeContext, delta_seconds: float) -> None:
        """Run one gameplay update tick."""

    def shutdown(self, context: RuntimeContext) -> None:
        """Release system resources."""


@dataclass(frozen=True, slots=True)
class SystemSpec:
    """System registration entry for update-loop ordering."""

    system_id: str
    system: GameplaySystem
    order: int = 0


@dataclass(frozen=True, slots=True)
class StateSnapshot[TState]:
    """Versioned state snapshot from state-store."""

    value: TState
    revision: int


class StateStore(Protocol[TState]):
    """Typed state-store contract for gameplay state."""

    def snapshot(self) -> StateSnapshot[TState]:
        """Return current state snapshot."""

    def get(self) -> TState:
        """Return current state value."""

    def peek(self) -> TState:
        """Return current state value reference without copying."""

    def set(self, value: TState) -> StateSnapshot[TState]:
        """Replace state value and increment revision."""

    def update(self, mutator: Callable[[TState], TState]) -> StateSnapshot[TState]:
        """Apply mutator and increment revision."""

    def revision(self) -> int:
        """Return current revision number."""


class UpdateLoop(Protocol):
    """Ordered gameplay update-loop contract."""

    def add_system(self, spec: SystemSpec) -> None:
        """Register system for lifecycle execution."""

    def start(self, context: RuntimeContext) -> None:
        """Start systems in order."""

    def step(self, context: RuntimeContext, delta_seconds: float) -> int:
        """Run one update frame and return number of ticks executed."""

    def shutdown(self, context: RuntimeContext) -> None:
        """Shutdown started systems in reverse order."""


def create_state_store[TState](initial_state: TState) -> StateStore[TState]:
    """Create default state-store implementation."""
    from engine.gameplay.state_store import RuntimeStateStore

    return RuntimeStateStore(initial_state)


def create_update_loop(*, fixed_step_seconds: float | None = None) -> UpdateLoop:
    """Create default gameplay update-loop implementation."""
    from engine.gameplay.update_loop import RuntimeUpdateLoop

    return RuntimeUpdateLoop(fixed_step_seconds=fixed_step_seconds)

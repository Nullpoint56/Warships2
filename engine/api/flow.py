"""Public flow/state-machine API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FlowContext[TState]:
    """Transition execution context."""

    trigger: str
    source: TState
    target: TState
    payload: object | None = None


type TransitionGuard[TState] = Callable[[FlowContext[TState]], bool]
type TransitionHook[TState] = Callable[[FlowContext[TState]], None]


@dataclass(frozen=True, slots=True)
class FlowTransition[TState]:
    """Public transition definition."""

    trigger: str
    source: TState | None
    target: TState
    guard: TransitionGuard[TState] | None = None
    before: TransitionHook[TState] | None = None
    after: TransitionHook[TState] | None = None


class FlowMachine[TState](Protocol):
    """Public flow-machine contract."""

    @property
    def state(self) -> TState:
        """Return current state."""

    def add_transition(self, transition: FlowTransition[TState]) -> None:
        """Register one transition."""

    def trigger(self, event: str, *, payload: object | None = None) -> bool:
        """Execute first matching transition."""


class FlowProgram[TState](Protocol):
    """Reusable transition program for stateless state-resolution queries."""

    def resolve(
        self, current_state: TState, trigger: str, *, payload: object | None = None
    ) -> TState | None:
        """Resolve next state for a trigger from a given state."""


def create_flow_machine[TState](initial_state: TState) -> FlowMachine[TState]:
    """Create default engine flow-machine implementation."""
    from engine.runtime.flow import RuntimeFlowMachine

    return RuntimeFlowMachine(initial_state)


def create_flow_program[TState](
    transitions: tuple[FlowTransition[TState], ...],
) -> FlowProgram[TState]:
    """Create reusable transition program implementation."""
    from engine.runtime.flow import RuntimeFlowProgram

    return RuntimeFlowProgram(transitions)

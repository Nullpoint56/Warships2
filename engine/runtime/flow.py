"""Generic state-flow transition executor."""

from __future__ import annotations

from engine.api.flow import FlowContext, FlowPayload, FlowTransition


class RuntimeFlowMachine[TState]:
    """Deterministic transition table executor."""

    def __init__(self, initial_state: TState) -> None:
        self._state = initial_state
        self._transitions: list[FlowTransition[TState]] = []

    @property
    def state(self) -> TState:
        return self._state

    def add_transition(self, transition: FlowTransition[TState]) -> None:
        """Register one transition."""
        self._transitions.append(transition)

    def trigger(self, event: str, *, payload: FlowPayload | None = None) -> bool:
        """Execute first matching transition. Returns whether state changed."""
        source_state = self._state
        for transition in self._transitions:
            if transition.trigger != event:
                continue
            if transition.source is not None and transition.source != source_state:
                continue
            context = FlowContext(
                trigger=event,
                source=source_state,
                target=transition.target,
                payload=payload,
            )
            if transition.guard is not None and not transition.guard(context):
                continue
            if transition.before is not None:
                transition.before(context)
            self._state = transition.target
            if transition.after is not None:
                transition.after(context)
            return True
        return False


FlowMachine = RuntimeFlowMachine


class RuntimeFlowProgram[TState]:
    """Reusable transition table for resolving next state from trigger."""

    def __init__(self, transitions: tuple[FlowTransition[TState], ...]) -> None:
        self._transitions = transitions

    def resolve(
        self, current_state: TState, trigger: str, *, payload: FlowPayload | None = None
    ) -> TState | None:
        for transition in self._transitions:
            if transition.trigger != trigger:
                continue
            if transition.source is not None and transition.source != current_state:
                continue
            context = FlowContext(
                trigger=trigger,
                source=current_state,
                target=transition.target,
                payload=payload,
            )
            if transition.guard is not None and not transition.guard(context):
                continue
            if transition.before is not None:
                transition.before(context)
            if transition.after is not None:
                transition.after(context)
            return transition.target
        return None

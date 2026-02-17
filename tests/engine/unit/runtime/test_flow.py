from __future__ import annotations

from dataclasses import dataclass

from engine.runtime.flow import FlowMachine, FlowTransition


@dataclass(frozen=True, slots=True)
class _Payload:
    value: int


def test_flow_machine_transitions_on_matching_trigger() -> None:
    machine = FlowMachine("main")
    machine.add_transition(FlowTransition(trigger="start", source="main", target="battle"))
    changed = machine.trigger("start")
    assert changed
    assert machine.state == "battle"


def test_flow_machine_respects_guard_and_hooks() -> None:
    machine = FlowMachine("main")
    before: list[str] = []
    after: list[str] = []

    def guard(context) -> bool:
        payload = context.payload
        return isinstance(payload, _Payload) and payload.value > 0

    def before_hook(context) -> None:
        before.append(f"{context.source}->{context.target}")

    def after_hook(context) -> None:
        after.append(context.trigger)

    machine.add_transition(
        FlowTransition(
            trigger="start",
            source="main",
            target="battle",
            guard=guard,
            before=before_hook,
            after=after_hook,
        )
    )

    assert not machine.trigger("start", payload=_Payload(0))
    assert machine.state == "main"
    assert machine.trigger("start", payload=_Payload(1))
    assert machine.state == "battle"
    assert before == ["main->battle"]
    assert after == ["start"]


def test_flow_machine_supports_wildcard_source() -> None:
    machine = FlowMachine("a")
    machine.add_transition(FlowTransition(trigger="reset", source=None, target="main"))
    assert machine.trigger("reset")
    assert machine.state == "main"

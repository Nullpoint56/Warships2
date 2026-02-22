from __future__ import annotations

from engine.api.flow import FlowTransition
from engine.runtime.flow import RuntimeFlowProgram


def test_flow_program_resolves_matching_transition() -> None:
    program = RuntimeFlowProgram(
        (
            FlowTransition(trigger="go", source="A", target="B"),
            FlowTransition(trigger="go", source="B", target="C"),
        )
    )
    assert program.resolve("A", "go") == "B"
    assert program.resolve("B", "go") == "C"
    assert program.resolve("C", "go") is None

from __future__ import annotations

from engine.api.ai import DecisionContext, create_blackboard, create_functional_agent


def test_functional_agent_decide() -> None:
    blackboard = create_blackboard()
    blackboard.set("mode", "hunt")
    agent = create_functional_agent(
        lambda context: "fire" if context.blackboard.require("mode") == "hunt" else "wait"
    )
    action = agent.decide(
        DecisionContext(
            now_seconds=1.0,
            delta_seconds=0.016,
            blackboard=blackboard,
            observations={"enemy_visible": True},
        )
    )
    assert action == "fire"

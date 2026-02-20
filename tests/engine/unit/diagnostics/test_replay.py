from __future__ import annotations

from pathlib import Path

from engine.diagnostics import FixedStepReplayRunner, ReplayRecorder, compute_state_hash


def test_replay_recorder_manifest_and_commands() -> None:
    recorder = ReplayRecorder(enabled=True, seed=1337, build={"engine_versions": {}}, hub=None)
    recorder.record_command(
        tick=2,
        command_type="input.key",
        payload={"event_type": "key_down", "value": "space"},
    )
    recorder.mark_frame(tick=2)
    recorder.mark_frame(tick=3)

    manifest = recorder.manifest()
    assert manifest.seed == 1337
    assert manifest.command_count == 1
    assert manifest.first_tick == 2
    assert manifest.last_tick == 3


def test_replay_recorder_export_json(tmp_path: Path) -> None:
    recorder = ReplayRecorder(enabled=True, seed=None, build={"build_id": "x"}, hub=None)
    recorder.record_command(
        tick=1,
        command_type="input.pointer",
        payload={"event_type": "pointer_move", "x": 1.0, "y": 2.0, "button": 0},
    )
    out = recorder.export_json(path=tmp_path / "replay.json", limit=200)
    assert out.exists()
    assert "diag.replay_session.v1" in out.read_text(encoding="utf-8")


def test_replay_runner_validates_checkpoint_hashes() -> None:
    session = {
        "manifest": {"first_tick": 1, "last_tick": 3},
        "commands": [
            {"tick": 1, "type": "inc", "payload": {"value": 2}},
            {"tick": 2, "type": "inc", "payload": {"value": 1}},
        ],
        "state_hashes": [
            {"tick": 2, "hash": compute_state_hash({"counter": 3})},
            {"tick": 3, "hash": compute_state_hash({"counter": 3})},
        ],
    }
    state = {"counter": 0}

    def apply_command(command) -> None:
        if command.command_type == "inc":
            state["counter"] += int(command.payload.get("value", 0))

    def step(_dt: float) -> dict[str, int]:
        return {"counter": state["counter"]}

    result = FixedStepReplayRunner(fixed_step_seconds=1.0 / 60.0).run(
        session, apply_command=apply_command, step=step
    )
    assert result.passed is True
    assert result.commands_applied == 2
    assert result.checkpoint_count == 2


def test_replay_runner_is_deterministic_from_logical_action_stream_only() -> None:
    session = {
        "manifest": {"first_tick": 1, "last_tick": 3},
        "commands": [
            {"tick": 1, "type": "input.action", "payload": {"name": "cursor.right", "phase": "start"}},
            {"tick": 2, "type": "input.action", "payload": {"name": "cursor.right", "phase": "end"}},
            {"tick": 2, "type": "input.action", "payload": {"name": "cursor.down", "phase": "start"}},
            {"tick": 3, "type": "input.action", "payload": {"name": "cursor.down", "phase": "end"}},
        ],
        "state_hashes": [
            {"tick": 1, "hash": compute_state_hash({"x": 1, "y": 0, "active": ["cursor.right"]})},
            {"tick": 2, "hash": compute_state_hash({"x": 1, "y": 1, "active": ["cursor.down"]})},
            {"tick": 3, "hash": compute_state_hash({"x": 1, "y": 1, "active": []})},
        ],
    }
    state = {"x": 0, "y": 0, "active": set()}

    def apply_command(command) -> None:
        if command.command_type != "input.action":
            return
        name = str(command.payload.get("name", ""))
        phase = str(command.payload.get("phase", ""))
        if phase == "start":
            state["active"].add(name)
        elif phase == "end":
            state["active"].discard(name)

    def step(_dt: float) -> dict[str, object]:
        if "cursor.right" in state["active"]:
            state["x"] += 1
        if "cursor.down" in state["active"]:
            state["y"] += 1
        return {"x": state["x"], "y": state["y"], "active": sorted(state["active"])}

    result = FixedStepReplayRunner(fixed_step_seconds=1.0 / 60.0).run(
        session, apply_command=apply_command, step=step
    )
    assert result.passed is True
    assert result.commands_applied == 4
    assert result.checkpoint_count == 3

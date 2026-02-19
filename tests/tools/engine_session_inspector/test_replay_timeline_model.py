from __future__ import annotations

from tools.engine_obs_core.contracts import FramePoint, ReplayCheckpointRecord, ReplayCommandRecord
from tools.engine_obs_core.datasource.base import ReplaySession
from tools.engine_session_inspector.views.replay import build_replay_timeline_model


def test_build_replay_timeline_model_tracks_commands_and_checkpoints() -> None:
    replay = ReplaySession(
        commands=[
            ReplayCommandRecord(tick=1, type="input.key", payload={}),
            ReplayCommandRecord(tick=1, type="input.pointer", payload={}),
            ReplayCommandRecord(tick=3, type="input.key", payload={}),
        ],
        checkpoints=[
            ReplayCheckpointRecord(tick=1, hash="abc"),
            ReplayCheckpointRecord(tick=3, hash="def"),
        ],
    )
    frames = [
        FramePoint(tick=1, frame_ms=16.0, render_ms=6.0, fps_rolling=60.0),
        FramePoint(tick=2, frame_ms=16.0, render_ms=6.0, fps_rolling=60.0),
        FramePoint(tick=3, frame_ms=25.0, render_ms=10.0, fps_rolling=40.0),
    ]

    model = build_replay_timeline_model(replay, frames)

    assert model.frame_ticks == [1, 2, 3]
    assert model.command_count_by_tick[1] == 2
    assert model.command_count_by_tick[3] == 1
    assert model.checkpoint_hash_by_tick[1] == "abc"
    assert model.checkpoint_mismatch_ticks == []
    assert model.max_command_density == 2


def test_build_replay_timeline_model_handles_empty_inputs() -> None:
    replay = ReplaySession(commands=[], checkpoints=[])
    model = build_replay_timeline_model(replay, [])
    assert model.frame_ticks == []
    assert model.command_count_by_tick == {}
    assert model.checkpoint_hash_by_tick == {}
    assert model.checkpoint_mismatch_ticks == []
    assert model.max_command_density == 0


def test_build_replay_timeline_model_detects_checkpoint_hash_mismatch() -> None:
    replay = ReplaySession(
        commands=[],
        checkpoints=[
            ReplayCheckpointRecord(tick=7, hash="aaa"),
            ReplayCheckpointRecord(tick=7, hash="bbb"),
            ReplayCheckpointRecord(tick=9, hash="ccc"),
        ],
    )
    model = build_replay_timeline_model(replay, [])
    assert model.checkpoint_hash_by_tick[7] == "aaa"
    assert model.checkpoint_mismatch_ticks == [7]

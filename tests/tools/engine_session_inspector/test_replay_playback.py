from __future__ import annotations

from tools.engine_session_inspector.views.replay import (
    clamp_index,
    frame_interval_ms,
    next_playback_index,
    step_index,
)


def test_replay_playback_index_helpers() -> None:
    assert clamp_index(5, 3) == 2
    assert clamp_index(-1, 3) == 0
    assert clamp_index(0, 0) == 0

    assert step_index(1, 1, 4) == 2
    assert step_index(3, 1, 4) == 3
    assert step_index(0, -2, 4) == 0

    assert next_playback_index(0, 4, loop=False) == 1
    assert next_playback_index(3, 4, loop=False) == 3
    assert next_playback_index(3, 4, loop=True) == 0


def test_replay_frame_interval_ms_bounds() -> None:
    assert frame_interval_ms(60.0) >= 16
    assert frame_interval_ms(120.0) >= 8
    assert frame_interval_ms(0.0) >= 1

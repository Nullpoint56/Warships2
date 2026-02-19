"""Replay view helpers for session inspector."""

from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.contracts import FramePoint
from tools.engine_obs_core.datasource.base import ReplaySession


@dataclass(frozen=True)
class ReplayTimelineModel:
    frame_ticks: list[int]
    command_count_by_tick: dict[int, int]
    checkpoint_hash_by_tick: dict[int, str]
    checkpoint_mismatch_ticks: list[int]
    max_command_density: int


def build_replay_timeline_model(
    replay: ReplaySession,
    frame_points: list[FramePoint],
) -> ReplayTimelineModel:
    frame_ticks = [int(point.tick) for point in frame_points]

    command_count_by_tick: dict[int, int] = {}
    for command in replay.commands:
        tick = int(command.tick)
        command_count_by_tick[tick] = command_count_by_tick.get(tick, 0) + 1

    checkpoint_hash_by_tick: dict[int, str] = {}
    checkpoint_mismatch_set: set[int] = set()
    for checkpoint in replay.checkpoints:
        tick = int(checkpoint.tick)
        value = str(checkpoint.hash)
        existing = checkpoint_hash_by_tick.get(tick)
        if existing is None:
            checkpoint_hash_by_tick[tick] = value
            continue
        if existing != value:
            checkpoint_mismatch_set.add(tick)

    max_density = max(command_count_by_tick.values()) if command_count_by_tick else 0
    return ReplayTimelineModel(
        frame_ticks=frame_ticks,
        command_count_by_tick=command_count_by_tick,
        checkpoint_hash_by_tick=checkpoint_hash_by_tick,
        checkpoint_mismatch_ticks=sorted(checkpoint_mismatch_set),
        max_command_density=max_density,
    )


def clamp_index(index: int, count: int) -> int:
    if count <= 0:
        return 0
    return max(0, min(int(index), count - 1))


def step_index(current: int, delta: int, count: int) -> int:
    return clamp_index(int(current) + int(delta), count)


def next_playback_index(current: int, count: int, *, loop: bool = False) -> int:
    if count <= 0:
        return 0
    if current + 1 < count:
        return current + 1
    return 0 if loop else count - 1


def frame_interval_ms(target_fps: float) -> int:
    fps = float(target_fps)
    if fps <= 0.0:
        fps = 60.0
    return max(1, int(round(1000.0 / fps)))

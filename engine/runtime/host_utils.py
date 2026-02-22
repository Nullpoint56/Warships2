"""Helper functions for EngineHost snapshot/profiling/replay handling."""

from __future__ import annotations

from engine.api.render_snapshot import (
    RenderCommand,
    RenderDataValue,
    RenderPassSnapshot,
    RenderSnapshot,
)
from engine.runtime.config import RuntimeHostConfig


def merge_render_snapshots(
    left: RenderSnapshot | None, right: RenderSnapshot | None
) -> RenderSnapshot | None:
    if left is None:
        return right
    if right is None:
        return left
    return RenderSnapshot(
        frame_index=left.frame_index,
        passes=tuple(left.passes) + tuple(right.passes),
    )


def sanitize_render_snapshot(snapshot: RenderSnapshot) -> RenderSnapshot:
    passes = tuple(
        RenderPassSnapshot(
            name=str(render_pass.name),
            commands=tuple(
                RenderCommand(
                    kind=str(command.kind),
                    layer=int(command.layer),
                    sort_key=str(command.sort_key),
                    transform=command.transform,
                    data=tuple((str(key), freeze_render_value(value)) for key, value in command.data),
                )
                for command in render_pass.commands
            ),
        )
        for render_pass in snapshot.passes
    )
    return RenderSnapshot(frame_index=int(snapshot.frame_index), passes=passes)


def freeze_render_value(value: object) -> RenderDataValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, tuple):
        return tuple(freeze_render_value(item) for item in value)
    if isinstance(value, list):
        return tuple(freeze_render_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), freeze_render_value(item)) for key, item in value.items())
        )
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((freeze_render_value(item) for item in value), key=str))
    return repr(value)


def profiling_snapshot_payload(snapshot: object) -> dict[str, object]:
    spans_raw = getattr(snapshot, "spans", [])
    spans: list[dict[str, object]] = []
    for span in spans_raw:
        spans.append(
            {
                "tick": int(getattr(span, "tick", 0)),
                "category": str(getattr(span, "category", "")),
                "name": str(getattr(span, "name", "")),
                "duration_ms": float(getattr(span, "duration_ms", 0.0)),
                "metadata": dict(getattr(span, "metadata", {}) or {}),
            }
        )
    top = list(getattr(snapshot, "top_spans_ms", []))
    return {
        "mode": str(getattr(snapshot, "mode", "off")),
        "span_count": int(getattr(snapshot, "span_count", len(spans))),
        "top_spans_ms": top,
        "spans": spans,
    }


def resolve_replay_seed(config: RuntimeHostConfig) -> int | None:
    raw = str(config.replay_seed or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def resolve_runtime_name(value: str) -> str:
    normalized = str(value).strip().lower()
    return normalized or "game"

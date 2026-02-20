from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from engine.api.input_events import KeyEvent, PointerEvent
from engine.api.input_snapshot import InputSnapshot
from engine.runtime.host import EngineHost
from engine.runtime.metrics import MetricsSnapshot


class FakeModule:
    def __init__(self) -> None:
        self.started = 0
        self.pointer_events = 0
        self.key_events = 0
        self.wheel_events = 0
        self.frames: list[tuple[int, float, float]] = []
        self.shutdown_calls = 0
        self._should_close = False

    def on_start(self, host) -> None:
        _ = host
        self.started += 1

    def on_pointer_event(self, event) -> bool:
        _ = event
        self.pointer_events += 1
        return True

    def on_key_event(self, event) -> bool:
        _ = event
        self.key_events += 1
        return True

    def on_wheel_event(self, event) -> bool:
        _ = event
        self.wheel_events += 1
        return True

    def on_frame(self, context) -> None:
        self.frames.append((context.frame_index, context.delta_seconds, context.elapsed_seconds))
        if context.frame_index >= 1:
            self._should_close = True

    def on_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        _ = snapshot
        return False

    def simulate(self, context) -> None:
        self.on_frame(context)

    def build_render_snapshot(self):
        return None

    def should_close(self) -> bool:
        return self._should_close

    def on_shutdown(self) -> None:
        self.shutdown_calls += 1


class _ScheduledCloseModule:
    def __init__(self) -> None:
        self.frame_calls = 0

    def on_start(self, host) -> None:
        host.call_later(0.0, host.close)

    def on_pointer_event(self, event) -> bool:
        _ = event
        return False

    def on_key_event(self, event) -> bool:
        _ = event
        return False

    def on_wheel_event(self, event) -> bool:
        _ = event
        return False

    def on_frame(self, context) -> None:
        _ = context
        self.frame_calls += 1

    def on_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        _ = snapshot
        return False

    def simulate(self, context) -> None:
        _ = context

    def build_render_snapshot(self):
        return None

    def should_close(self) -> bool:
        return False

    def on_shutdown(self) -> None:
        return


class _FakeRenderer:
    def __init__(self) -> None:
        self.rect_calls: list[str] = []
        self.text_calls: list[str] = []
        self.text_values: list[str] = []
        self.invalidates = 0

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (x, y)

    def add_rect(self, key, x, y, w, h, color, z=0.0, static=False) -> None:
        _ = (x, y, w, h, color, z, static)
        self.rect_calls.append(str(key))

    def add_text(
        self,
        key,
        text,
        x,
        y,
        font_size=18.0,
        color="#ffffff",
        anchor="top-left",
        z=2.0,
        static=False,
    ) -> None:
        _ = (text, x, y, font_size, color, anchor, z, static)
        self.text_calls.append(str(key))
        self.text_values.append(str(text))

    def invalidate(self) -> None:
        self.invalidates += 1


def test_engine_host_lifecycle_and_close() -> None:
    module = FakeModule()
    host = EngineHost(module=module)
    host.frame()
    host.frame()
    assert module.started == 1
    assert [frame_index for frame_index, _, _ in module.frames] == [0, 1]
    assert module.frames[0][1] == 0.0
    assert module.frames[0][2] == 0.0
    assert module.frames[1][1] >= 0.0
    assert module.frames[1][2] >= module.frames[1][1]
    assert host.is_closed()
    assert module.shutdown_calls == 1


def test_engine_host_forwards_input_events() -> None:
    module = FakeModule()
    host = EngineHost(module=module)
    assert host.handle_pointer_event(object()) is True
    assert host.handle_key_event(object()) is True
    assert host.handle_wheel_event(object()) is True
    assert (module.pointer_events, module.key_events, module.wheel_events) == (1, 1, 1)


def test_engine_host_handles_input_snapshot() -> None:
    module = FakeModule()
    host = EngineHost(module=module)
    snapshot = InputSnapshot(
        frame_index=0,
        pointer_events=(PointerEvent(event_type="pointer_down", x=1.0, y=2.0, button=1),),
        key_events=(KeyEvent(event_type="key_down", value="a"),),
    )
    assert host.handle_input_snapshot(snapshot) is False
    assert module.pointer_events == 0
    assert module.key_events == 0


def test_engine_host_stops_before_frame_when_scheduled_close_fires() -> None:
    module = _ScheduledCloseModule()
    host = EngineHost(module=module)
    host.frame()
    assert host.is_closed()
    assert module.frame_calls == 0


def test_engine_host_exposes_metrics_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    module = FakeModule()
    host = EngineHost(module=module)

    host.frame()
    snapshot = host.metrics_snapshot

    assert isinstance(snapshot, MetricsSnapshot)
    assert snapshot.last_frame is not None
    assert snapshot.last_frame.frame_index == 0
    assert snapshot.last_frame.scheduler_queue_size >= 0


def test_engine_host_draws_debug_overlay_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DEBUG_OVERLAY", "1")
    module = FakeModule()
    renderer = _FakeRenderer()
    host = EngineHost(module=module, render_api=renderer)

    host.frame()
    assert renderer.text_calls == []

    handled = host.handle_key_event(KeyEvent(event_type="key_down", value="f3"))
    assert handled is True
    assert renderer.invalidates == 1

    host.frame()

    assert any(":line:" in key for key in renderer.text_calls)


def test_engine_host_overlay_includes_ui_diagnostics_summary_when_available(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DEBUG_OVERLAY", "1")
    module = FakeModule()
    renderer = _FakeRenderer()

    def _summary() -> dict[str, int]:
        return {"revision": 9, "resize_seq": 42, "anomaly_count": 2}

    renderer.ui_diagnostics_summary = _summary  # type: ignore[attr-defined]
    host = EngineHost(module=module, render_api=renderer)
    host.handle_key_event(KeyEvent(event_type="key_down", value="f3"))
    host.frame()

    assert any(text.startswith("UI rev=9 resize=42 anomalies=2") for text in renderer.text_values)


def test_engine_host_emits_profile_records_when_enabled(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DEBUG_PROFILING", "1")
    monkeypatch.setenv("ENGINE_DEBUG_PROFILING_SAMPLING_N", "1")
    caplog.set_level(logging.INFO, logger="engine.profiling")

    module = FakeModule()
    host = EngineHost(module=module)
    host.frame()

    messages = [
        record.getMessage() for record in caplog.records if record.name == "engine.profiling"
    ]
    assert any("frame_profile" in message for message in messages)
    prof_records = [record for record in caplog.records if record.name == "engine.profiling"]
    assert prof_records
    assert isinstance(getattr(prof_records[0], "profile", None), dict)


def test_engine_host_emits_frame_events_to_diagnostics_hub(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    module = FakeModule()
    host = EngineHost(module=module)

    host.frame()
    events = host.diagnostics_hub.snapshot(limit=20, category="frame")

    names = [event.name for event in events]
    assert "frame.start" in names
    assert "frame.time_ms" in names
    assert "frame.end" in names


class _ExplodingModule(FakeModule):
    def on_frame(self, context) -> None:
        _ = context
        raise RuntimeError("host-frame-failure")


class _HashingModule(FakeModule):
    def debug_state_hash(self) -> dict[str, int]:
        return {"frames": len(self.frames)}


def test_engine_host_writes_crash_bundle_on_frame_exception(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENGINE_DIAG_CRASH_BUNDLE", "1")
    monkeypatch.setenv("ENGINE_DIAG_CRASH_DIR", str(tmp_path))
    host = EngineHost(module=_ExplodingModule())

    with pytest.raises(RuntimeError):
        host.frame()

    bundles = sorted(tmp_path.glob("engine_crash_bundle_*.json"))
    assert bundles
    payload = json.loads(bundles[-1].read_text(encoding="utf-8"))
    assert payload["schema_version"] == "engine.crash_bundle.v1"
    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["exception"]["message"] == "host-frame-failure"
    assert payload["recent_events"]


def test_engine_host_emits_perf_events_when_diag_timeline_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DIAG_PROFILE_MODE", "timeline")
    host = EngineHost(module=FakeModule())

    host.frame()
    span_events = host.diagnostics_hub.snapshot(category="perf", name="perf.span")
    assert span_events


def test_engine_host_records_replay_input_and_manifest(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAG_REPLAY_CAPTURE", "1")
    monkeypatch.setenv("WARSHIPS_RNG_SEED", "12345")
    host = EngineHost(module=FakeModule())

    host.handle_key_event(KeyEvent(event_type="key_down", value="a"))
    host.frame()

    manifest = host.diagnostics_replay_manifest
    assert int(getattr(manifest, "seed", 0)) == 12345
    assert int(getattr(manifest, "command_count", 0)) >= 1
    replay_events = host.diagnostics_hub.snapshot(category="replay", name="replay.command")
    assert replay_events


def test_engine_host_records_replay_state_hash_when_provider_available(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAG_REPLAY_CAPTURE", "1")
    monkeypatch.setenv("ENGINE_DIAG_REPLAY_HASH_INTERVAL", "1")
    host = EngineHost(module=_HashingModule())
    host.frame()
    host.frame()

    hash_events = host.diagnostics_hub.snapshot(category="replay", name="replay.state_hash")
    assert hash_events

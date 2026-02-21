from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from engine.api.input_events import KeyEvent, PointerEvent
from engine.api.input_snapshot import ActionSnapshot, ControllerSnapshot, InputSnapshot
from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.runtime.host import EngineHost
from engine.runtime.metrics import MetricsSnapshot


class FakeModule:
    def __init__(self) -> None:
        self.started = 0
        self.snapshots: list[InputSnapshot] = []
        self.frames: list[tuple[int, float, float]] = []
        self.shutdown_calls = 0
        self._should_close = False

    def on_start(self, host) -> None:
        _ = host
        self.started += 1

    def on_frame(self, context) -> None:
        self.frames.append((context.frame_index, context.delta_seconds, context.elapsed_seconds))
        if context.frame_index >= 1:
            self._should_close = True

    def on_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        self.snapshots.append(snapshot)
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
        self.snapshots: list[RenderSnapshot] = []

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

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        self.snapshots.append(snapshot)
        for render_pass in snapshot.passes:
            for command in render_pass.commands:
                data = {str(key): value for key, value in command.data}
                if command.kind == "text":
                    key = data.get("key")
                    text = data.get("text")
                    self.text_calls.append(str(key))
                    self.text_values.append(str(text))

    def design_space_size(self) -> tuple[float, float]:
        return (1920.0, 1080.0)


class _SnapshotModule(FakeModule):
    def __init__(self) -> None:
        super().__init__()
        self.payload: list[str] = ["base"]

    def build_render_snapshot(self) -> RenderSnapshot:
        command = RenderCommand(
            kind="text",
            data=(("key", "mod:text"), ("text", self.payload), ("x", 100.0), ("y", 100.0)),
        )
        return RenderSnapshot(
            frame_index=len(self.frames),
            passes=(RenderPassSnapshot(name="main", commands=(command,)),),
        )

    def ui_design_resolution(self) -> tuple[float, float]:
        return (1200.0, 720.0)


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


def test_engine_host_submits_module_snapshot_to_renderer() -> None:
    module = _SnapshotModule()
    renderer = _FakeRenderer()
    host = EngineHost(module=module, render_api=renderer)

    host.frame()

    assert len(renderer.snapshots) == 1
    submitted = renderer.snapshots[0]
    assert submitted.frame_index == len(module.frames)
    assert submitted.passes[0].commands[0].kind == "text"
    payload = dict(submitted.passes[0].commands[0].data)
    assert payload["x"] == pytest.approx(160.0)
    assert payload["y"] == pytest.approx(150.0)


def test_engine_host_detaches_snapshot_payload_from_live_state() -> None:
    module = _SnapshotModule()
    renderer = _FakeRenderer()
    host = EngineHost(module=module, render_api=renderer)

    host.frame()
    module.payload.append("mutated")

    submitted = renderer.snapshots[0]
    data = dict(submitted.passes[0].commands[0].data)
    assert data["text"] == ("base",)


def test_engine_host_can_skip_snapshot_sanitize_for_perf(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_RUNTIME_RENDER_SNAPSHOT_SANITIZE", "0")
    module = _SnapshotModule()
    renderer = _FakeRenderer()
    host = EngineHost(module=module, render_api=renderer)

    host.frame()
    module.payload.append("mutated")

    submitted = renderer.snapshots[0]
    data = dict(submitted.passes[0].commands[0].data)
    assert data["text"] == ["base", "mutated"]


def test_engine_host_handles_input_snapshot() -> None:
    module = FakeModule()
    host = EngineHost(module=module)
    snapshot = InputSnapshot(
        frame_index=0,
        pointer_events=(PointerEvent(event_type="pointer_down", x=1.0, y=2.0, button=1),),
        key_events=(KeyEvent(event_type="key_down", value="a"),),
    )
    assert host.handle_input_snapshot(snapshot) is False
    assert len(module.snapshots) == 1


def test_engine_host_replay_records_logical_actions_from_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", "1")
    host = EngineHost(module=FakeModule())
    snapshot = InputSnapshot(
        frame_index=0,
        actions=ActionSnapshot(
            just_started=frozenset({"action.confirm"}),
            just_ended=frozenset({"action.cancel"}),
        ),
        key_events=(KeyEvent(event_type="key_down", value="a"),),
    )
    host.handle_input_snapshot(snapshot)
    replay = host.diagnostics_replay_snapshot
    commands = list(replay.get("commands", []))
    types = [str(item.get("type", "")) for item in commands]
    assert types.count("input.action") == 2
    assert "input.key" not in types


def test_engine_host_snapshot_overlay_toggle_uses_logical_action(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_OVERLAY_ENABLED", "1")
    renderer = _FakeRenderer()
    host = EngineHost(module=FakeModule(), render_api=renderer)
    snapshot = InputSnapshot(
        frame_index=0,
        actions=ActionSnapshot(just_started=frozenset({"engine.debug_overlay.toggle"})),
        key_events=(KeyEvent(event_type="key_down", value="f3"),),
    )
    assert host.handle_input_snapshot(snapshot) is True
    assert renderer.invalidates == 1


def test_engine_host_emits_input_diagnostics_for_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    host = EngineHost(module=FakeModule())
    snapshot = InputSnapshot(
        frame_index=0,
        actions=ActionSnapshot(values=(("meta.mapping_conflicts", 1.0),)),
        controllers=(ControllerSnapshot(device_id="pad-1", connected=True),),
    )
    host.handle_input_snapshot(snapshot)
    freq = host.diagnostics_hub.snapshot(category="input", name="input.event_frequency")
    assert freq
    conflicts = host.diagnostics_hub.snapshot(category="input", name="input.mapping_conflict")
    assert conflicts
    connected = host.diagnostics_hub.snapshot(category="input", name="input.device_connected")
    assert connected


def test_engine_host_stops_before_frame_when_scheduled_close_fires() -> None:
    module = _ScheduledCloseModule()
    host = EngineHost(module=module)
    host.frame()
    assert host.is_closed()
    assert module.frame_calls == 0


def test_engine_host_exposes_metrics_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    module = FakeModule()
    host = EngineHost(module=module)

    host.frame()
    snapshot = host.metrics_snapshot

    assert isinstance(snapshot, MetricsSnapshot)
    assert snapshot.last_frame is not None
    assert snapshot.last_frame.frame_index == 0
    assert snapshot.last_frame.scheduler_queue_size >= 0


def test_engine_host_draws_debug_overlay_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_UI_OVERLAY_ENABLED", "1")
    module = FakeModule()
    renderer = _FakeRenderer()
    host = EngineHost(module=module, render_api=renderer)

    host.frame()
    assert renderer.text_calls == []

    handled = host.handle_input_snapshot(
        InputSnapshot(
            frame_index=1,
            actions=ActionSnapshot(just_started=frozenset({"engine.debug_overlay.toggle"})),
            key_events=(KeyEvent(event_type="key_down", value="f3"),),
        )
    )
    assert handled is True
    assert renderer.invalidates == 1

    host.frame()

    assert any(":line:" in key for key in renderer.text_calls)


def test_engine_host_emits_profile_records_when_enabled(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_SAMPLING_N", "1")
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
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
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
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_CRASH_ENABLED", "1")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_CRASH_DIR", str(tmp_path))
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
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_PROFILING_MODE", "timeline")
    host = EngineHost(module=FakeModule())

    host.frame()
    span_events = host.diagnostics_hub.snapshot(category="perf", name="perf.span")
    assert span_events


def test_engine_host_records_replay_input_and_manifest(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", "1")
    monkeypatch.setenv("WARSHIPS_RNG_SEED", "12345")
    host = EngineHost(module=FakeModule())

    host.handle_input_snapshot(
        InputSnapshot(
            frame_index=0,
            actions=ActionSnapshot(just_started=frozenset({"action.confirm"})),
            key_events=(KeyEvent(event_type="key_down", value="a"),),
        )
    )
    host.frame()

    manifest = host.diagnostics_replay_manifest
    assert int(getattr(manifest, "seed", 0)) == 12345
    assert int(getattr(manifest, "command_count", 0)) >= 1
    replay_events = host.diagnostics_hub.snapshot(category="replay", name="replay.command")
    assert replay_events


def test_engine_host_records_replay_state_hash_when_provider_available(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", "1")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_HASH_INTERVAL", "1")
    host = EngineHost(module=_HashingModule())
    host.frame()
    host.frame()

    hash_events = host.diagnostics_hub.snapshot(category="replay", name="replay.state_hash")
    assert hash_events


def test_engine_host_emits_capture_ready_and_profile_capture_state(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_SAMPLING_N", "1")
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_FRAMES", "2")
    monkeypatch.setenv("ENGINE_PROFILING_CAPTURE_EXPORT_DIR", str(tmp_path))

    host = EngineHost(module=FakeModule())
    host.frame()
    host.frame()

    ready_events = host.diagnostics_hub.snapshot(category="perf", name="perf.host_capture_ready")
    assert ready_events
    value = ready_events[-1].value
    assert isinstance(value, dict)
    captured_frames = int(value.get("captured_frames", 0))
    assert 1 <= captured_frames <= 2
    report_path = value.get("path")
    assert isinstance(report_path, str) and report_path
    assert Path(report_path).exists()

    profile_events = host.diagnostics_hub.snapshot(category="perf", name="perf.frame_profile")
    assert profile_events
    profile = profile_events[-1].value
    assert isinstance(profile, dict)
    capture = profile.get("capture")
    assert isinstance(capture, dict)
    assert capture.get("state") in {"capturing", "complete"}


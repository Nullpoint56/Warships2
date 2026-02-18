from __future__ import annotations

from engine.runtime.metrics import MetricsSnapshot
from engine.runtime.host import EngineHost


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

    def should_close(self) -> bool:
        return False

    def on_shutdown(self) -> None:
        return


class _FakeRenderer:
    def __init__(self) -> None:
        self.rect_calls: list[str] = []
        self.text_calls: list[str] = []

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

    assert any(key.endswith(":bg") for key in renderer.rect_calls)
    assert any(":line:" in key for key in renderer.text_calls)

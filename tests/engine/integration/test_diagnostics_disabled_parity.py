from __future__ import annotations

from types import SimpleNamespace

import engine.rendering.scene as scene_mod
from engine.runtime.debug_config import DebugConfig


class _FakeCanvas:
    def __init__(self, size=(1200, 720), title="") -> None:
        self._size = size
        self._title = title
        self._draw_cb = None
        self.handlers: list[tuple[object, str]] = []

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.append((handler, event_type))

    def get_logical_size(self):
        return self._size

    def request_draw(self, cb=None):
        if cb is not None:
            self._draw_cb = cb
            return
        if self._draw_cb is not None:
            self._draw_cb()

    def close(self) -> None:
        return


class _FakeRenderer:
    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.render_calls = 0

    def render(self, scene, camera) -> None:
        _ = (scene, camera)
        self.render_calls += 1


class _FakeScene:
    def add(self, node) -> None:
        _ = node


class _FakeOrthoCamera:
    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height
        self.local = SimpleNamespace(position=(0, 0, 0), scale_y=1.0)


class _FakeGfx:
    WgpuRenderer = _FakeRenderer
    Scene = _FakeScene
    OrthographicCamera = _FakeOrthoCamera


def test_diagnostics_disabled_parity_keeps_runtime_behavior(monkeypatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(
        scene_mod,
        "load_debug_config",
        lambda: DebugConfig(
            metrics_enabled=False,
            overlay_enabled=False,
            ui_trace_enabled=False,
            resize_trace_enabled=False,
            ui_trace_sampling_n=10,
            log_level="INFO",
            ui_trace_auto_dump=False,
            ui_trace_dump_dir="appdata/logs",
        ),
    )

    renderer = scene_mod.SceneRenderer(width=1200, height=720)
    assert renderer._ui_diagnostics is None

    resize_handler = next(handler for handler, event in renderer.canvas.handlers if event == "resize")
    resize_handler({"width": 1400.0, "height": 800.0})
    renderer.canvas._size = (1400.0, 800.0)
    renderer.note_frame_reason("input:pointer")

    drew: list[str] = []

    def draw_cb() -> None:
        drew.append("drawn")

    renderer.run(draw_cb)

    assert drew == ["drawn"]
    assert renderer.width == 1400
    assert renderer.height == 800
    assert renderer.renderer.render_calls == 1

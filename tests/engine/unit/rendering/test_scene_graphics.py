from __future__ import annotations

from types import SimpleNamespace

import pytest

import engine.rendering.scene as scene_mod


@pytest.mark.graphics
def test_scene_renderer_raises_when_pygfx_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scene_mod, "gfx", None)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", ModuleNotFoundError("pygfx missing"))
    with pytest.raises(RuntimeError, match="pygfx dependency unavailable"):
        scene_mod.SceneRenderer()


@pytest.mark.graphics
def test_scene_renderer_raises_when_canvas_backend_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scene_mod, "gfx", object())
    monkeypatch.setattr(scene_mod, "rc_auto", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", RuntimeError("backend missing"))
    with pytest.raises(RuntimeError, match="Render canvas backend unavailable"):
        scene_mod.SceneRenderer()


class _FakeCanvas:
    def __init__(self, size=(1200, 720), title="") -> None:
        self._size = size
        self._physical_size = size
        self._pixel_ratio = 1.0
        self._title = title
        self._draw_cb = None
        self.closed = False
        self.handlers: list[tuple[object, str]] = []
        self.request_draw_count = 0

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.append((handler, event_type))

    def get_logical_size(self):
        return self._size

    def get_physical_size(self):
        return self._physical_size

    def get_pixel_ratio(self):
        return self._pixel_ratio

    def set_title(self, title: str) -> None:
        self._title = title

    def request_draw(self, cb=None):
        if cb is not None:
            self._draw_cb = cb
            return
        self.request_draw_count += 1
        if self._draw_cb is not None:
            self._draw_cb()

    def close(self) -> None:
        self.closed = True


class _FakeRenderer:
    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.render_calls = 0
        self.pixel_ratio = 2.0
        self.target = SimpleNamespace(_pixel_ratio=1.0)

    def render(self, scene, camera) -> None:
        _ = (scene, camera)
        self.render_calls += 1


class _FakeScene:
    def __init__(self) -> None:
        self.nodes = []

    def add(self, node) -> None:
        self.nodes.append(node)


class _FakeOrthoCamera:
    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height
        self.local = SimpleNamespace(position=(0, 0, 0), scale_y=1.0)
        self.set_view_size_calls: list[tuple[float, float]] = []

    def set_view_size(self, width: float, height: float) -> None:
        self.set_view_size_calls.append((width, height))


class _FakeGfx:
    WgpuRenderer = _FakeRenderer
    Scene = _FakeScene
    OrthographicCamera = _FakeOrthoCamera


@pytest.mark.graphics
def test_scene_renderer_fake_backend_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    calls: list[str] = []

    def draw_cb() -> None:
        calls.append("draw")

    renderer.run(draw_cb)
    assert calls == ["draw"]
    assert renderer.renderer.render_calls == 1


@pytest.mark.graphics
def test_scene_renderer_locks_viewport_within_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)

    revisions: list[int] = []

    def capture_upsert_rect(**kwargs) -> None:
        revisions.append(int(kwargs["viewport_revision"]))

    monkeypatch.setattr(scene_mod, "upsert_rect", capture_upsert_rect)

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    first_revision = renderer._viewport_revision  # noqa: SLF001 - verifying renderer internals

    renderer.begin_frame()
    renderer.add_rect("a", 0.0, 0.0, 10.0, 10.0, "#fff")
    renderer._on_resize({"width": 500.0, "height": 300.0})  # noqa: SLF001 - simulate backend event
    resized_revision = renderer._viewport_revision  # noqa: SLF001
    renderer.add_rect("b", 0.0, 0.0, 10.0, 10.0, "#fff")
    renderer.end_frame()

    assert resized_revision > first_revision
    assert revisions == [first_revision, first_revision]

    renderer.begin_frame()
    renderer.add_rect("c", 0.0, 0.0, 10.0, 10.0, "#fff")
    renderer.end_frame()
    assert revisions[-1] == resized_revision


@pytest.mark.graphics
def test_scene_renderer_exposes_ui_trace_scope_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE", "1")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    decorator = renderer.ui_trace_scope("draw:probe")
    assert decorator is not None


@pytest.mark.graphics
def test_scene_renderer_forces_invalidate_on_resize_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_FORCE_INVALIDATE", "1")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    resize_handler = next(
        handler for handler, event in renderer.canvas.handlers if event == "resize"
    )
    before = renderer.canvas.request_draw_count
    resize_handler({"width": 400.0, "height": 250.0})
    assert renderer.canvas.request_draw_count == before + 1


@pytest.mark.graphics
def test_scene_renderer_uses_round_quantization_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SIZE_QUANTIZATION", "round")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    resize_handler = next(
        handler for handler, event in renderer.canvas.handlers if event == "resize"
    )
    resize_handler({"width": 400.6, "height": 250.6})
    assert renderer.width == 401
    assert renderer.height == 251


@pytest.mark.graphics
def test_scene_renderer_skips_canvas_sync_in_event_only_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SIZE_SOURCE_MODE", "event_only")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    renderer.canvas._size = (900.0, 700.0)

    renderer.run(lambda: None)

    assert renderer.width == 300
    assert renderer.height == 200


@pytest.mark.graphics
def test_scene_renderer_calls_set_view_size_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_CAMERA_SET_VIEW_SIZE", "1")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    resize_handler = next(
        handler for handler, event in renderer.canvas.handlers if event == "resize"
    )
    resize_handler({"width": 420.0, "height": 260.0})
    assert renderer.camera.set_view_size_calls
    assert renderer.camera.set_view_size_calls[-1] == (420.0, 260.0)


@pytest.mark.graphics
def test_scene_renderer_can_force_renderer_pixel_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RENDERER_FORCE_PIXEL_RATIO", "1.0")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    assert renderer.renderer.pixel_ratio == 1.0
    assert renderer.renderer.target._pixel_ratio == 1.0
    runtime = renderer._resolve_runtime_info()  # noqa: SLF001
    assert runtime["backend_experiment"]["renderer_force_pixel_ratio"] == 1.0


@pytest.mark.graphics
def test_scene_renderer_can_sync_from_physical_size(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_auto = SimpleNamespace(RenderCanvas=_FakeCanvas)
    monkeypatch.setattr(scene_mod, "gfx", _FakeGfx)
    monkeypatch.setattr(scene_mod, "rc_auto", fake_auto)
    monkeypatch.setattr(scene_mod, "_gfx_import_error", None)
    monkeypatch.setattr(scene_mod, "_canvas_import_error", None)
    monkeypatch.setattr(scene_mod, "run_backend_loop", lambda rc_auto: None)
    monkeypatch.setattr(scene_mod, "stop_backend_loop", lambda rc_auto: None)
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SYNC_FROM_PHYSICAL_SIZE", "1")
    monkeypatch.setenv("ENGINE_DEBUG_RENDERER_FORCE_PIXEL_RATIO", "1.0")

    renderer = scene_mod.SceneRenderer(width=300, height=200)
    renderer.canvas._physical_size = (800.0, 600.0)
    renderer.canvas._size = (300.0, 200.0)
    renderer.run(lambda: None)
    assert renderer.width == 800
    assert renderer.height == 600

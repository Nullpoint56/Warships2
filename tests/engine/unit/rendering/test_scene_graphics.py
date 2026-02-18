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
        self._title = title
        self._draw_cb = None
        self.closed = False
        self.handlers: list[tuple[object, str]] = []

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.append((handler, event_type))

    def get_logical_size(self):
        return self._size

    def set_title(self, title: str) -> None:
        self._title = title

    def request_draw(self, cb=None):
        if cb is not None:
            self._draw_cb = cb
            return
        if self._draw_cb is not None:
            self._draw_cb()

    def close(self) -> None:
        self.closed = True


class _FakeRenderer:
    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.render_calls = 0

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

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

    def render(self, scene, camera) -> None:
        _ = (scene, camera)


class _FakeScene:
    def add(self, node) -> None:
        _ = node


class _FakeOrthoCamera:
    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height
        self.local = SimpleNamespace(position=(0, 0, 0), scale_y=1.0)


class _FakeGeometry:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


class _FakeTextGeometry:
    def __init__(self, markdown: str, font_size: float, anchor: str) -> None:
        self.markdown = markdown
        self.font_size = font_size
        self.anchor = anchor


class _FakeMesh:
    def __init__(self, geometry, material) -> None:
        self.geometry = geometry
        self.material = material
        self.local = SimpleNamespace(position=(0, 0, 0))
        self.visible = True


class _FakeLine:
    def __init__(self, geometry, material) -> None:
        self.geometry = geometry
        self.material = material
        self.local = SimpleNamespace(position=(0, 0, 0))
        self.visible = True


class _FakeText:
    def __init__(
        self,
        text: str,
        font_size: float,
        screen_space: bool,
        material,
        anchor: str | None = None,
    ) -> None:
        self.text = text
        self.font_size = font_size
        self.screen_space = screen_space
        self.material = material
        self.anchor = anchor
        self.local = SimpleNamespace(position=(0, 0, 0))
        self.visible = True


class _FakeGfx:
    WgpuRenderer = _FakeRenderer
    Scene = _FakeScene
    OrthographicCamera = _FakeOrthoCamera
    Mesh = _FakeMesh
    Line = _FakeLine
    Text = _FakeText
    Geometry = _FakeGeometry
    TextGeometry = _FakeTextGeometry

    @staticmethod
    def plane_geometry(width: float, height: float) -> _FakeGeometry:
        return _FakeGeometry(width, height)

    @staticmethod
    def line_geometry(positions=None, colors=None) -> _FakeGeometry:
        _ = (positions, colors)
        return _FakeGeometry(0.0, 0.0)

    @staticmethod
    def MeshBasicMaterial(color: str) -> object:
        return SimpleNamespace(color=color)

    @staticmethod
    def LineMaterial(color: str, thickness: float, thickness_space: str = "screen") -> object:
        return SimpleNamespace(color=color, thickness=thickness, thickness_space=thickness_space)

    @staticmethod
    def TextMaterial(color: str) -> object:
        return SimpleNamespace(color=color)


def test_resize_input_and_button_diagnostics_pipeline(monkeypatch) -> None:
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
            ui_trace_enabled=True,
            ui_trace_sampling_n=1,
            resize_trace_enabled=True,
            log_level="DEBUG",
            ui_trace_auto_dump=False,
            ui_trace_dump_dir="appdata/logs",
        ),
    )

    renderer = scene_mod.SceneRenderer(width=1200, height=720)
    resize_handler = next(handler for handler, event in renderer.canvas.handlers if event == "resize")
    resize_handler({"width": 1400.0, "height": 800.0, "size": (1400.0, 800.0), "pixel_ratio": 1.0})
    renderer.canvas._size = (1400.0, 800.0)
    renderer.note_frame_reason("input:pointer")

    def draw_cb() -> None:
        renderer.add_rect("button:bg:new_game", 100.0, 100.0, 120.0, 40.0, "#2244cc")
        renderer.add_text("button:text:new_game", "New Game", 110.0, 110.0, font_size=18.0)

    renderer.run(draw_cb)

    diagnostics = renderer._ui_diagnostics
    assert diagnostics is not None
    frames = diagnostics.recent_frames()
    assert len(frames) == 1

    frame = frames[0]
    reasons = frame.get("reasons")
    assert isinstance(reasons, list)
    assert "input:pointer" in reasons

    resize_payload = frame.get("resize")
    assert isinstance(resize_payload, dict)
    assert resize_payload.get("event_size") == [1400.0, 800.0]
    assert resize_payload.get("applied_size") == [1400, 800]

    viewport = frame.get("viewport")
    assert isinstance(viewport, dict)
    assert viewport.get("width") == 1400
    assert viewport.get("height") == 800

    buttons = frame.get("buttons")
    assert isinstance(buttons, dict)
    new_game = buttons.get("new_game")
    assert isinstance(new_game, dict)
    assert "rect" in new_game
    assert "text_size" in new_game

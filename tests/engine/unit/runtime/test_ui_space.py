from __future__ import annotations

from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.runtime.ui_space import create_app_render_api, resolve_ui_space_transform


class _Renderer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def begin_frame(self) -> None:
        return

    def end_frame(self) -> None:
        return

    def add_rect(self, key, x, y, w, h, color, z=0.0, static=False) -> None:
        self.calls.append(("rect", (key, x, y, w, h, color, z, static)))

    def add_grid(self, key, x, y, width, height, lines, color, z=0.5, static=False) -> None:
        self.calls.append(("grid", (key, x, y, width, height, lines, color, z, static)))

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
        self.calls.append(("text", (key, text, x, y, font_size, color, anchor, z, static)))

    def set_title(self, title: str) -> None:
        _ = title

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        self.calls.append(("fill_window", (key, color, z)))

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (x, y)

    def invalidate(self) -> None:
        return

    def run(self, draw_callback) -> None:
        draw_callback()

    def close(self) -> None:
        return

    def render_snapshot(self, snapshot) -> None:
        self.calls.append(("snapshot", (snapshot,)))

    def design_space_size(self) -> tuple[float, float]:
        return (1920.0, 1080.0)


class _App:
    def ui_design_resolution(self) -> tuple[float, float]:
        return (1200.0, 720.0)


def test_resolve_ui_space_transform_uses_app_resolution() -> None:
    transform = resolve_ui_space_transform(app=_App(), renderer=_Renderer())
    assert transform.scale_x == 1.6
    assert transform.scale_y == 1.5


def test_create_app_render_api_scales_draw_commands() -> None:
    renderer = _Renderer()
    app_renderer = create_app_render_api(app=_App(), renderer=renderer)

    app_renderer.add_rect("r", 100.0, 100.0, 50.0, 20.0, "#fff")
    app_renderer.add_text("t", "x", 200.0, 120.0, font_size=20.0)

    rect_payload = renderer.calls[0][1]
    text_payload = renderer.calls[1][1]
    assert rect_payload[1] == 160.0
    assert rect_payload[2] == 150.0
    assert rect_payload[3] == 80.0
    assert rect_payload[4] == 30.0
    assert text_payload[2] == 320.0
    assert text_payload[3] == 180.0
    assert text_payload[4] == 30.0


def test_create_app_render_api_scales_render_snapshot_payload() -> None:
    renderer = _Renderer()
    app_renderer = create_app_render_api(app=_App(), renderer=renderer)
    snapshot = RenderSnapshot(
        frame_index=1,
        passes=(
            RenderPassSnapshot(
                name="ui",
                commands=(
                    RenderCommand(
                        kind="rect",
                        data=(("x", 100.0), ("y", 100.0), ("w", 50.0), ("h", 20.0)),
                    ),
                    RenderCommand(
                        kind="text",
                        data=(("x", 200.0), ("y", 120.0), ("font_size", 20.0)),
                    ),
                ),
            ),
        ),
    )

    app_renderer.render_snapshot(snapshot)
    scaled_snapshot = renderer.calls[0][1][0]
    rect_data = dict(scaled_snapshot.passes[0].commands[0].data)
    text_data = dict(scaled_snapshot.passes[0].commands[1].data)
    assert rect_data["x"] == 160.0
    assert rect_data["y"] == 150.0
    assert rect_data["w"] == 80.0
    assert rect_data["h"] == 30.0
    assert text_data["x"] == 320.0
    assert text_data["y"] == 180.0
    assert text_data["font_size"] == 30.0

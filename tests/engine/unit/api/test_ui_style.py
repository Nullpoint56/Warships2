from __future__ import annotations

from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_gradient_rect,
    draw_rounded_rect,
    draw_shadow_rect,
    draw_stroke_rect,
)


class _Renderer:
    def __init__(self) -> None:
        self.rects: list[tuple[tuple, dict]] = []

    def add_rect(self, *args, **kwargs) -> None:
        self.rects.append((args, kwargs))


class _StyleRenderer(_Renderer):
    def __init__(self) -> None:
        super().__init__()
        self.style_calls: list[dict[str, object]] = []

    def add_style_rect(self, **kwargs) -> None:
        self.style_calls.append(dict(kwargs))


def test_default_ui_style_tokens_are_deterministic() -> None:
    assert DEFAULT_UI_STYLE_TOKENS.window_bg == "#0b132b"
    assert DEFAULT_UI_STYLE_TOKENS.accent == "#1f6feb"
    assert DEFAULT_UI_STYLE_TOKENS.text_primary == "#f9fafb"


def test_draw_stroke_rect_emits_four_rects(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "1")
    renderer = _Renderer()
    draw_stroke_rect(
        renderer,
        key="box",
        x=10.0,
        y=20.0,
        w=100.0,
        h=60.0,
        color="#ffffff",
    )
    assert len(renderer.rects) == 4


def test_draw_gradient_rect_emits_requested_strip_count(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "1")
    renderer = _Renderer()
    draw_gradient_rect(
        renderer,
        key="grad",
        x=0.0,
        y=0.0,
        w=80.0,
        h=24.0,
        top_color="#ffffffff",
        bottom_color="#00000000",
        steps=6,
    )
    assert len(renderer.rects) == 6


def test_draw_shadow_rect_emits_layered_rects(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "1")
    renderer = _Renderer()
    draw_shadow_rect(
        renderer,
        key="shadow",
        x=0.0,
        y=0.0,
        w=30.0,
        h=12.0,
        layers=3,
    )
    assert len(renderer.rects) == 3


def test_draw_rounded_rect_emits_multiple_segments_for_radius(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "1")
    renderer = _Renderer()
    draw_rounded_rect(
        renderer,
        key="rounded",
        x=0.0,
        y=0.0,
        w=40.0,
        h=20.0,
        radius=6.0,
        color="#ffffff",
    )
    assert len(renderer.rects) > 4


def test_style_effects_disabled_defaults_to_fast_path(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "0")
    renderer = _Renderer()
    draw_gradient_rect(
        renderer,
        key="grad",
        x=0.0,
        y=0.0,
        w=80.0,
        h=24.0,
        top_color="#ffffffff",
        bottom_color="#00000000",
        steps=6,
    )
    draw_shadow_rect(renderer, key="shadow", x=0.0, y=0.0, w=10.0, h=10.0)
    draw_rounded_rect(
        renderer,
        key="rounded",
        x=0.0,
        y=0.0,
        w=10.0,
        h=10.0,
        radius=5.0,
        color="#ffffff",
    )
    assert len(renderer.rects) == 1


def test_style_helpers_use_single_command_path_when_renderer_supports_it(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_UI_STYLE_EFFECTS", "1")
    renderer = _StyleRenderer()
    draw_rounded_rect(
        renderer,
        key="rounded",
        x=1.0,
        y=2.0,
        w=10.0,
        h=12.0,
        radius=4.0,
        color="#ffffff",
    )
    draw_gradient_rect(
        renderer,
        key="grad",
        x=0.0,
        y=0.0,
        w=20.0,
        h=8.0,
        top_color="#ffffffff",
        bottom_color="#00000000",
    )
    assert len(renderer.style_calls) == 2
    assert renderer.style_calls[0]["style_kind"] == "rounded_rect"
    assert renderer.style_calls[1]["style_kind"] == "gradient_rect"
    assert renderer.rects == []

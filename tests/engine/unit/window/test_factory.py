from __future__ import annotations

import pytest

import engine.window.factory as factory


def test_create_window_layer_uses_rendercanvas_backend(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setenv("ENGINE_WINDOW_BACKEND", "rendercanvas_glfw")
    monkeypatch.setattr(factory, "create_rendercanvas_window", lambda **kwargs: sentinel)

    out = factory.create_window_layer(
        width=800,
        height=600,
        title="x",
        update_mode="ondemand",
        min_fps=0.0,
        max_fps=240.0,
        vsync=True,
    )

    assert out is sentinel


def test_create_window_layer_rejects_direct_glfw_backend(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_WINDOW_BACKEND", "direct_glfw")

    with pytest.raises(RuntimeError, match="not supported"):
        factory.create_window_layer(
            width=800,
            height=600,
            title="x",
            update_mode="ondemand",
            min_fps=0.0,
            max_fps=240.0,
            vsync=True,
        )


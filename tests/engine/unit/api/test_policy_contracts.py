from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from engine.api.input_snapshot import (
    InputSnapshot,
    KeyboardSnapshot,
    create_empty_input_snapshot,
)
from engine.api.render_snapshot import (
    Mat4,
    RenderCommand,
    RenderPassSnapshot,
    Vec3,
    create_render_snapshot,
    mat4_scale,
    mat4_translation,
)
from engine.api.window import (
    SurfaceHandle,
    WindowCloseEvent,
    WindowFocusEvent,
    WindowMinimizeEvent,
    WindowResizeEvent,
)


def test_input_snapshot_is_immutable() -> None:
    snapshot = InputSnapshot(frame_index=3, keyboard=KeyboardSnapshot(pressed_keys=frozenset({"a"})))
    with pytest.raises(FrozenInstanceError):
        snapshot.frame_index = 4  # type: ignore[misc]


def test_create_empty_input_snapshot_defaults() -> None:
    snapshot = create_empty_input_snapshot(frame_index=7)
    assert snapshot.frame_index == 7
    assert snapshot.keyboard.pressed_keys == frozenset()
    assert snapshot.mouse.pressed_buttons == frozenset()
    assert snapshot.controllers == ()
    assert snapshot.actions.active == frozenset()


def test_mat4_requires_exact_16_values() -> None:
    with pytest.raises(ValueError, match="16"):
        Mat4(values=(1.0, 2.0))


def test_render_snapshot_structure() -> None:
    cmd = RenderCommand(kind="rect", layer=1, data=(("color", "#ffffff"),))
    render_pass = RenderPassSnapshot(name="ui", commands=(cmd,))
    snapshot = create_render_snapshot(frame_index=9, passes=(render_pass,))
    assert snapshot.frame_index == 9
    assert snapshot.passes[0].name == "ui"
    assert snapshot.passes[0].commands[0].kind == "rect"


def test_render_snapshot_dimension_neutral_helpers() -> None:
    translation = mat4_translation(Vec3(2.0, 3.0, 4.0))
    scale = mat4_scale(Vec3(10.0, 11.0, 12.0))
    assert translation.values[3] == 2.0
    assert translation.values[7] == 3.0
    assert translation.values[11] == 4.0
    assert scale.values[0] == 10.0
    assert scale.values[5] == 11.0
    assert scale.values[10] == 12.0


def test_window_contract_values_are_normalized_shape() -> None:
    surface = SurfaceHandle(surface_id="main", backend="glfw")
    assert surface.surface_id == "main"
    assert surface.backend == "glfw"

    resize = WindowResizeEvent(
        logical_width=1280.0,
        logical_height=720.0,
        physical_width=1920,
        physical_height=1080,
        dpi_scale=1.5,
    )
    assert resize.logical_width == 1280.0
    assert resize.physical_width == 1920
    assert resize.dpi_scale == 1.5

    assert WindowFocusEvent(focused=True).focused is True
    assert WindowMinimizeEvent(minimized=False).minimized is False
    assert WindowCloseEvent().requested is True

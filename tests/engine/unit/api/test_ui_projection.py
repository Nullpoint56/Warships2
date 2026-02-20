from __future__ import annotations

from engine.api.ui_primitives import Rect
from engine.api.ui_projection import ButtonSpec, project_buttons


def test_project_buttons_filters_by_condition() -> None:
    buttons = project_buttons(
        (
            ButtonSpec("a", 0, 0, 10, 10),
            ButtonSpec("b", 0, 0, 10, 10, when=False),
        )
    )
    assert [button.id for button in buttons] == ["a"]


def test_project_buttons_can_clamp_to_container() -> None:
    buttons = project_buttons(
        (
            ButtonSpec("a", -5.0, -5.0, 20.0, 20.0),
            ButtonSpec("b", 90.0, 90.0, 20.0, 20.0),
        ),
        container=Rect(0.0, 0.0, 100.0, 100.0),
        clamp_to_container=True,
        pad_x=4.0,
        pad_y=4.0,
    )

    assert buttons[0].x >= 4.0 and buttons[0].y >= 4.0
    assert buttons[1].x + buttons[1].w <= 96.0
    assert buttons[1].y + buttons[1].h <= 96.0

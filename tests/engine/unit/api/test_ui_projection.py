from __future__ import annotations

from engine.api.ui_projection import ButtonSpec, project_buttons


def test_project_buttons_filters_by_condition() -> None:
    buttons = project_buttons(
        (
            ButtonSpec("a", 0, 0, 10, 10),
            ButtonSpec("b", 0, 0, 10, 10, when=False),
        )
    )
    assert [button.id for button in buttons] == ["a"]

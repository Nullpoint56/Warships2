import pytest

from engine.ui_runtime.grid_layout import GridLayout


def test_rect_for_primary_and_secondary() -> None:
    layout = GridLayout(
        primary_origin_x=10, secondary_origin_x=100, origin_y=5, cell_size=4, grid_size=3
    )
    primary = layout.rect_for_target("primary")
    secondary = layout.rect_for_target("secondary")
    assert (primary.x, primary.y, primary.w, primary.h) == (10, 5, 12, 12)
    assert (secondary.x, secondary.y, secondary.w, secondary.h) == (100, 5, 12, 12)


def test_target_names_and_unknown_target() -> None:
    layout = GridLayout()
    assert layout.rect_for_target("primary").x == layout.primary_origin_x
    assert layout.rect_for_target("secondary").x == layout.secondary_origin_x
    with pytest.raises(ValueError):
        layout.rect_for_target("player")
    with pytest.raises(ValueError):
        layout.rect_for_target("enemy")
    with pytest.raises(ValueError):
        layout.rect_for_target("not-a-target")


def test_screen_to_cell_bounds_and_edges() -> None:
    layout = GridLayout(primary_origin_x=0, origin_y=0, cell_size=10, grid_size=3)
    with pytest.raises(ValueError):
        layout.screen_to_cell("self", 0, 0)
    top_left = layout.screen_to_cell("primary", 0, 0)
    assert top_left is not None
    assert (top_left.row, top_left.col) == (0, 0)
    bottom_right = layout.screen_to_cell("primary", 29.99, 29.99)
    assert bottom_right is not None
    assert (bottom_right.row, bottom_right.col) == (2, 2)
    assert layout.screen_to_cell("primary", 30, 30) is None
    assert layout.screen_to_cell("primary", -1, 0) is None

from engine.api.ui_primitives import (
    Rect,
    clamp_child_rect_to_parent,
    fit_text_to_rect,
    parent_rect_from_children,
    truncate_text,
)


def test_truncate_text_uses_ellipsis_when_possible() -> None:
    assert truncate_text("abc", 5) == "abc"
    assert truncate_text("abcdef", 3) == "abc"
    assert truncate_text("abcdef", 5) == "ab..."


def test_fit_text_to_rect_enforces_bounds_with_truncation() -> None:
    text, size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=180.0,
        rect_h=44.0,
        base_font_size=14.0,
    )
    assert len(text) < len("Generate Random Fleet")
    assert text.endswith("...")
    assert size <= 16.0


def test_clamp_child_rect_to_parent_enforces_bounds() -> None:
    child = Rect(x=-10.0, y=5.0, w=100.0, h=80.0)
    parent = Rect(x=0.0, y=0.0, w=60.0, h=40.0)

    clamped = clamp_child_rect_to_parent(child, parent, pad_x=4.0, pad_y=2.0)

    assert clamped.x >= 4.0
    assert clamped.y >= 2.0
    assert clamped.x + clamped.w <= 56.0
    assert clamped.y + clamped.h <= 38.0


def test_parent_rect_from_children_fits_all_children_with_padding() -> None:
    parent = parent_rect_from_children(
        (
            Rect(10.0, 20.0, 30.0, 40.0),
            Rect(50.0, 10.0, 10.0, 10.0),
        ),
        pad_x=2.0,
        pad_y=3.0,
        min_w=20.0,
        min_h=10.0,
    )

    assert parent.x == 8.0
    assert parent.y == 7.0
    assert parent.w == 54.0
    assert parent.h == 56.0

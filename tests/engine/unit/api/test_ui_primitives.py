from engine.api.ui_primitives import (
    apply_text_overflow,
    clip_text,
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


def test_fit_text_to_rect_prefers_shrink_before_overflow() -> None:
    text, size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=180.0,
        rect_h=44.0,
        base_font_size=14.0,
    )
    assert text == "Generate Random Fleet"
    assert size <= 14.0


def test_fit_text_to_rect_supports_clip_policy() -> None:
    text, _size = fit_text_to_rect(
        "Generate Random Fleet",
        rect_w=120.0,
        rect_h=24.0,
        base_font_size=14.0,
        overflow_policy="clip",
    )
    assert not text.endswith("...")
    assert len(text) <= len("Generate Random Fleet")


def test_fit_text_to_rect_supports_wrap_none_policy() -> None:
    source = "Generate Random Fleet"
    text, _size = fit_text_to_rect(
        source,
        rect_w=80.0,
        rect_h=20.0,
        base_font_size=14.0,
        overflow_policy="wrap-none",
    )
    assert text == source


def test_apply_text_overflow_variants() -> None:
    assert clip_text("abcdef", 3) == "abc"
    assert apply_text_overflow("abcdef", 3, "clip") == "abc"
    assert apply_text_overflow("abcdef", 5, "ellipsis") == "ab..."
    assert apply_text_overflow("abcdef", 3, "wrap-none") == "abcdef"


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

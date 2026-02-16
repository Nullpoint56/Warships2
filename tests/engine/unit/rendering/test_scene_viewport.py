from engine.rendering.scene_viewport import extract_resize_dimensions, to_design_space, viewport_transform


def test_extract_resize_dimensions_from_multiple_payload_shapes() -> None:
    assert extract_resize_dimensions({"width": 100, "height": 200}) == (100.0, 200.0)
    assert extract_resize_dimensions({"size": (10, 20)}) == (10.0, 20.0)
    assert extract_resize_dimensions({"logical_size": [30, 40]}) == (30.0, 40.0)
    assert extract_resize_dimensions({"size": ("a", 1)}) == (None, None)


def test_viewport_transform_without_and_with_aspect_preservation() -> None:
    sx, sy, ox, oy = viewport_transform(
        width=200, height=100, design_width=100, design_height=100, preserve_aspect=False
    )
    assert (sx, sy, ox, oy) == (2.0, 1.0, 0.0, 0.0)

    sx, sy, ox, oy = viewport_transform(
        width=200, height=100, design_width=100, design_height=100, preserve_aspect=True
    )
    assert (sx, sy) == (1.0, 1.0)
    assert (ox, oy) == (50.0, 0.0)


def test_to_design_space_respects_offset_and_scale() -> None:
    x, y = to_design_space(
        x=75.0,
        y=20.0,
        width=200,
        height=100,
        design_width=100,
        design_height=100,
        preserve_aspect=True,
    )
    assert (x, y) == (25.0, 20.0)

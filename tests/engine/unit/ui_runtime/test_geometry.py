from engine.ui_runtime.geometry import Rect


def test_rect_contains_inside_and_edges() -> None:
    rect = Rect(10, 20, 30, 40)
    assert rect.contains(10, 20)
    assert rect.contains(40, 60)
    assert rect.contains(25, 35)


def test_rect_contains_outside() -> None:
    rect = Rect(10, 20, 30, 40)
    assert not rect.contains(9.99, 20)
    assert not rect.contains(10, 60.01)

from engine.ui_runtime.list_viewport import can_scroll_down, clamp_scroll, visible_slice


def test_visible_slice_clamps_scroll() -> None:
    items = [1, 2, 3, 4, 5]
    assert visible_slice(items, scroll=-5, visible_count=2) == [1, 2]
    assert visible_slice(items, scroll=99, visible_count=2) == [4, 5]


def test_can_scroll_down_boundaries() -> None:
    assert can_scroll_down(scroll=0, visible_count=2, total_count=5)
    assert not can_scroll_down(scroll=3, visible_count=2, total_count=5)


def test_clamp_scroll_limits() -> None:
    assert clamp_scroll(-1, visible_count=3, total_count=10) == 0
    assert clamp_scroll(99, visible_count=3, total_count=10) == 7

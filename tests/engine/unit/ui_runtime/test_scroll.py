from engine.ui_runtime.scroll import apply_wheel_scroll


def test_apply_wheel_scroll_up_and_down() -> None:
    assert apply_wheel_scroll(dy=-1.0, current_scroll=3, can_scroll_down=True).next_scroll == 2
    assert apply_wheel_scroll(dy=1.0, current_scroll=3, can_scroll_down=True).next_scroll == 4


def test_apply_wheel_scroll_noop_when_blocked() -> None:
    up_blocked = apply_wheel_scroll(dy=-1.0, current_scroll=0, can_scroll_down=True)
    down_blocked = apply_wheel_scroll(dy=1.0, current_scroll=2, can_scroll_down=False)
    assert not up_blocked.handled and up_blocked.next_scroll == 0
    assert not down_blocked.handled and down_blocked.next_scroll == 2

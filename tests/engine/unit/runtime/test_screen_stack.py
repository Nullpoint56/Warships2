from __future__ import annotations

import pytest

from engine.runtime.screen_stack import ScreenStack


def test_screen_stack_sets_root_and_resets_overlays() -> None:
    stack = ScreenStack()
    root = stack.set_root("main_menu")
    stack.push_overlay("settings")
    next_root = stack.set_root("battle")
    assert root.screen_id == "main_menu"
    assert next_root.screen_id == "battle"
    assert [layer.screen_id for layer in stack.layers()] == ["battle"]


def test_screen_stack_push_and_pop_overlay() -> None:
    stack = ScreenStack()
    stack.set_root("main_menu")
    stack.push_overlay("options")
    top = stack.top()
    popped = stack.pop_overlay()
    assert top is not None
    assert top.screen_id == "options"
    assert popped is not None
    assert popped.screen_id == "options"
    assert stack.top() is not None
    assert stack.top() is stack.root()


def test_screen_stack_rejects_overlay_without_root() -> None:
    stack = ScreenStack()
    with pytest.raises(RuntimeError):
        stack.push_overlay("invalid")

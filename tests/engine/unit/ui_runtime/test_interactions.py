from engine.ui_runtime.interactions import (
    can_scroll_with_wheel,
    resolve_pointer_button,
    route_non_modal_key_event,
)

from tests.engine.conftest import Box, FakeButton, FakeInteractionPlan


def test_resolve_pointer_button_uses_enabled_first_match() -> None:
    disabled = FakeButton("a", False, Box(0, 0, 50, 50))
    enabled = FakeButton("b", True, Box(0, 0, 50, 50))
    plan = FakeInteractionPlan(buttons=(disabled, enabled))
    assert resolve_pointer_button(plan, 10, 10) == "b"


def test_can_scroll_with_wheel_matches_any_region() -> None:
    plan = FakeInteractionPlan(wheel_scroll_regions=(Box(0, 0, 10, 10), Box(20, 20, 10, 10)))
    assert can_scroll_with_wheel(plan, 5, 5)
    assert can_scroll_with_wheel(plan, 25, 25)
    assert not can_scroll_with_wheel(plan, 50, 50)


def test_route_non_modal_key_event_char_and_key() -> None:
    plan = FakeInteractionPlan(shortcut_buttons={"r": "randomize"})
    char_route = route_non_modal_key_event("char", "x", plan)
    assert char_route.controller_char == "x"
    key_route = route_non_modal_key_event("key_down", "R", plan)
    assert key_route.controller_key == "r"
    assert key_route.shortcut_button_id == "randomize"
    ignored = route_non_modal_key_event("key_up", "R", plan)
    assert ignored.controller_key is None

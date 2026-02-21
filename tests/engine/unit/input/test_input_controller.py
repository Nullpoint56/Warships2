from __future__ import annotations

import pytest

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.input.input_controller import InputController


def test_consume_window_input_events_routes_supported_types() -> None:
    controller = InputController()
    controller.consume_window_input_events(
        (
            PointerEvent("pointer_down", 10.0, 20.0, 1),
            PointerEvent("pointer_move", 11.0, 21.0, 0),
            KeyEvent("key_down", "R"),
            KeyEvent("char", "x"),
            WheelEvent(11.0, 21.0, 1.25),
        )
    )
    assert [e.event_type for e in controller.drain_pointer_events()] == ["pointer_down", "pointer_move"]
    assert [e.event_type for e in controller.drain_key_events()] == ["key_down", "char"]
    wheels = controller.drain_wheel_events()
    assert len(wheels) == 1 and wheels[0].dy == 1.25


def test_pointer_down_left_click_only_and_drain() -> None:
    calls: list[str] = []
    controller = InputController(on_click_queued=lambda: calls.append("queued"))
    controller.consume_window_input_events((PointerEvent("pointer_down", 10.0, 20.0, 2),))
    non_left_pointer = controller.drain_pointer_events()
    assert len(non_left_pointer) == 1
    assert non_left_pointer[0].button == 2
    assert controller.drain_clicks() == []

    controller.consume_window_input_events((PointerEvent("pointer_down", 10.0, 20.0, 1),))
    pointer_events = controller.drain_pointer_events()
    clicks = controller.drain_clicks()
    assert len(pointer_events) == 1
    assert pointer_events[0].event_type == "pointer_down"
    assert len(clicks) == 1
    assert clicks[0].button == 1
    assert calls == ["queued", "queued"]


def test_move_up_key_char_wheel_queueing_and_clearing() -> None:
    controller = InputController()
    controller.consume_window_input_events(
        (
            PointerEvent("pointer_move", 5.0, 6.0, 0),
            PointerEvent("pointer_up", 5.0, 6.0, 1),
            KeyEvent("key_down", "R"),
            KeyEvent("char", "x"),
            WheelEvent(5.0, 6.0, 1.25),
        )
    )

    pointer_events = controller.drain_pointer_events()
    key_events = controller.drain_key_events()
    wheel_events = controller.drain_wheel_events()
    assert [e.event_type for e in pointer_events] == ["pointer_move", "pointer_up"]
    assert [e.event_type for e in key_events] == ["key_down", "char"]
    assert len(wheel_events) == 1 and wheel_events[0].dy == 1.25

    assert controller.drain_pointer_events() == []
    assert controller.drain_key_events() == []
    assert controller.drain_wheel_events() == []


def test_build_input_snapshot_is_frame_stable_and_immutable_views() -> None:
    controller = InputController()
    controller.consume_window_input_events(
        (
            PointerEvent("pointer_move", 10.0, 20.0, 0),
            PointerEvent("pointer_down", 10.0, 20.0, 1),
            KeyEvent("key_down", "A"),
            KeyEvent("char", "a"),
            WheelEvent(10.0, 20.0, 1.5),
        )
    )

    snapshot = controller.build_input_snapshot(frame_index=5)
    assert snapshot.frame_index == 5
    assert snapshot.mouse.x == 10
    assert snapshot.mouse.y == 20
    assert snapshot.mouse.just_pressed_buttons == frozenset({1})
    assert snapshot.keyboard.just_pressed_keys == frozenset({"a"})
    assert snapshot.keyboard.text_input == ("a",)
    assert snapshot.wheel_events[0].dy == 1.5
    assert controller.drain_pointer_events() == []
    assert controller.drain_key_events() == []
    assert controller.drain_wheel_events() == []


def test_build_input_snapshot_preserves_pressed_state_until_release() -> None:
    controller = InputController()
    controller.consume_window_input_events((KeyEvent("key_down", "Z"),))
    first = controller.build_input_snapshot(frame_index=1)
    second = controller.build_input_snapshot(frame_index=2)
    controller.consume_window_input_events((KeyEvent("key_up", "Z"),))
    third = controller.build_input_snapshot(frame_index=3)

    assert first.keyboard.just_pressed_keys == frozenset({"z"})
    assert second.keyboard.pressed_keys == frozenset({"z"})
    assert third.keyboard.just_released_keys == frozenset({"z"})
    assert third.keyboard.pressed_keys == frozenset()


def test_build_input_snapshot_resolves_bound_actions() -> None:
    controller = InputController()
    controller.bind_action_key_down("A", "action.move_left")
    controller.bind_action_pointer_down(1, "action.select")
    controller.bind_action_char("x", "action.type_x")

    controller.consume_window_input_events(
        (
            KeyEvent("key_down", "A"),
            PointerEvent("pointer_down", 1.0, 2.0, 1),
            KeyEvent("char", "x"),
        )
    )
    first = controller.build_input_snapshot(frame_index=1)
    assert first.actions.just_started == frozenset(
        {"action.move_left", "action.select", "action.type_x"}
    )
    assert first.actions.active == frozenset({"action.move_left", "action.select"})

    second = controller.build_input_snapshot(frame_index=2)
    assert second.actions.active == frozenset({"action.move_left", "action.select"})
    assert second.actions.just_started == frozenset()

    controller.consume_window_input_events(
        (
            KeyEvent("key_up", "A"),
            PointerEvent("pointer_up", 1.0, 2.0, 1),
        )
    )
    third = controller.build_input_snapshot(frame_index=3)
    assert third.actions.just_ended == frozenset({"action.move_left", "action.select"})
    assert third.actions.active == frozenset()


def test_action_binding_validation() -> None:
    controller = InputController()
    with pytest.raises(ValueError):
        controller.bind_action_key_down("   ", "a")
    with pytest.raises(ValueError):
        controller.bind_action_pointer_down(-1, "a")
    with pytest.raises(ValueError):
        controller.bind_action_char("", "a")


def test_action_binding_conflicts_are_reported_in_snapshot_values() -> None:
    controller = InputController()
    controller.bind_action_key_down("k", "action.one")
    controller.bind_action_key_down("k", "action.two")
    snapshot = controller.build_input_snapshot(frame_index=1)
    values = dict(snapshot.actions.values)
    assert values.get("meta.mapping_conflicts", 0.0) >= 1.0

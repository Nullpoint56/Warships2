from __future__ import annotations

import pytest

from engine.input.input_controller import InputController


class FakeCanvas:
    def __init__(self) -> None:
        self.handlers: dict[str, list] = {}

    def add_event_handler(self, handler, event_type: str) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def emit(self, event_type: str, **payload) -> None:
        event = {"event_type": event_type, **payload}
        for handler in self.handlers.get(event_type, []):
            handler(event)


def test_bind_registers_expected_handlers() -> None:
    canvas = FakeCanvas()
    controller = InputController()
    controller.bind(canvas)
    for event_name in (
        "pointer_down",
        "pointer_move",
        "pointer_up",
        "key_down",
        "key_up",
        "char",
        "wheel",
    ):
        assert event_name in canvas.handlers


def test_pointer_down_left_click_only_and_drain() -> None:
    calls: list[str] = []
    canvas = FakeCanvas()
    controller = InputController(on_click_queued=lambda: calls.append("queued"))
    controller.bind(canvas)

    canvas.emit("pointer_down", button=2, x=10, y=20)
    assert controller.drain_pointer_events() == []

    canvas.emit("pointer_down", button=1, x=10, y=20)
    pointer_events = controller.drain_pointer_events()
    clicks = controller.drain_clicks()
    assert len(pointer_events) == 1
    assert pointer_events[0].event_type == "pointer_down"
    assert len(clicks) == 1
    assert clicks[0].button == 1
    assert calls == ["queued"]


def test_move_up_key_char_wheel_queueing_and_clearing() -> None:
    canvas = FakeCanvas()
    controller = InputController()
    controller.bind(canvas)

    canvas.emit("pointer_move", x=5, y=6, button=0)
    canvas.emit("pointer_up", x=5, y=6, button=1)
    canvas.emit("key_down", key="R")
    canvas.emit("char", data="x")
    canvas.emit("wheel", x=5, y=6, dy=1.25)

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
    canvas = FakeCanvas()
    controller = InputController()
    controller.bind(canvas)

    canvas.emit("pointer_move", x=10, y=20, button=0)
    canvas.emit("pointer_down", x=10, y=20, button=1)
    canvas.emit("key_down", key="A")
    canvas.emit("char", data="a")
    canvas.emit("wheel", x=10, y=20, dy=1.5)

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
    canvas = FakeCanvas()
    controller = InputController()
    controller.bind(canvas)

    canvas.emit("key_down", key="Z")
    first = controller.build_input_snapshot(frame_index=1)
    second = controller.build_input_snapshot(frame_index=2)
    canvas.emit("key_up", key="Z")
    third = controller.build_input_snapshot(frame_index=3)

    assert first.keyboard.just_pressed_keys == frozenset({"z"})
    assert second.keyboard.pressed_keys == frozenset({"z"})
    assert third.keyboard.just_released_keys == frozenset({"z"})
    assert third.keyboard.pressed_keys == frozenset()


def test_build_input_snapshot_resolves_bound_actions() -> None:
    canvas = FakeCanvas()
    controller = InputController()
    controller.bind(canvas)
    controller.bind_action_key_down("A", "action.move_left")
    controller.bind_action_pointer_down(1, "action.select")
    controller.bind_action_char("x", "action.type_x")

    canvas.emit("key_down", key="A")
    canvas.emit("pointer_down", x=1, y=2, button=1)
    canvas.emit("char", data="x")
    first = controller.build_input_snapshot(frame_index=1)
    assert first.actions.just_started == frozenset(
        {"action.move_left", "action.select", "action.type_x"}
    )
    assert first.actions.active == frozenset({"action.move_left", "action.select"})

    second = controller.build_input_snapshot(frame_index=2)
    assert second.actions.active == frozenset({"action.move_left", "action.select"})
    assert second.actions.just_started == frozenset()

    canvas.emit("key_up", key="A")
    canvas.emit("pointer_up", x=1, y=2, button=1)
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

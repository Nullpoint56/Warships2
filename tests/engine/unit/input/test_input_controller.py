from __future__ import annotations

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
    for event_name in ("pointer_down", "pointer_move", "pointer_up", "key_down", "char", "wheel"):
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

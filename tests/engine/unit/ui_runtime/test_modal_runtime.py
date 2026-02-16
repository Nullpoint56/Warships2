from engine.ui_runtime.modal_runtime import ModalInputState, route_modal_key_event, route_modal_pointer_event

from tests.engine.conftest import FakeModalWidget


def test_modal_state_sync_open_close() -> None:
    state = ModalInputState()
    widget = FakeModalWidget()
    state.sync(widget)
    assert state.is_open
    assert state.input_focused
    state.sync(None)
    assert not state.is_open
    assert not state.input_focused


def test_modal_pointer_routing_targets() -> None:
    state = ModalInputState(is_open=True, input_focused=False)
    widget = FakeModalWidget()
    confirm = route_modal_pointer_event(widget, state, 15, 15, button=1)
    assert confirm.button_id == widget.confirm_button_id
    cancel = route_modal_pointer_event(widget, state, 45, 15, button=1)
    assert cancel.button_id == widget.cancel_button_id
    focus = route_modal_pointer_event(widget, state, 15, 45, button=1)
    assert focus.focus_input is True
    panel = route_modal_pointer_event(widget, state, 80, 80, button=1)
    assert panel.focus_input is False
    non_left = route_modal_pointer_event(widget, state, 15, 15, button=2)
    assert non_left.swallow and non_left.button_id is None
    outside = route_modal_pointer_event(widget, ModalInputState(is_open=True, input_focused=True), 500, 500, button=1)
    assert outside.focus_input is True


def test_modal_key_routing_input_focus_behavior() -> None:
    state = ModalInputState(is_open=True, input_focused=True)
    typed = route_modal_key_event("char", "a", mapped_key=None, state=state)
    assert typed.char == "a"
    backspace = route_modal_key_event("key_down", "Backspace", mapped_key="backspace", state=state)
    assert backspace.key == "backspace"
    escape = route_modal_key_event("key_down", "Escape", mapped_key="escape", state=state)
    assert escape.key == "escape"
    unmapped = route_modal_key_event("key_down", "F1", mapped_key=None, state=state)
    assert unmapped.swallow and unmapped.key is None and unmapped.char is None
    non_key = route_modal_key_event("pointer_down", "n/a", mapped_key=None, state=state)
    assert non_key.swallow
    no_focus_backspace = route_modal_key_event(
        "key_down",
        "Backspace",
        mapped_key="backspace",
        state=ModalInputState(is_open=True, input_focused=False),
    )
    assert no_focus_backspace.key is None

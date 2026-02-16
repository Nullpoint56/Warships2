from engine.ui_runtime.prompt_runtime import (
    close_prompt,
    handle_button,
    handle_char,
    handle_key,
    open_prompt,
    sync_prompt,
)


def test_open_sync_close_prompt() -> None:
    state = open_prompt(
        title="Save", initial_value="abc", confirm_button_id="prompt_confirm", mode="save"
    )
    assert state.prompt is not None
    assert state.buffer == "abc"
    synced = sync_prompt(state, "xyz")
    assert synced.buffer == "xyz"
    closed = close_prompt()
    assert closed.prompt is None and closed.buffer == ""


def test_prompt_button_confirm_and_cancel() -> None:
    state = open_prompt(title="Save", initial_value="", confirm_button_id="prompt_confirm")
    confirm = handle_button(state, "prompt_confirm")
    assert confirm.handled and confirm.request_confirm
    cancel = handle_button(state, "prompt_cancel")
    assert cancel.handled and cancel.state.prompt is None and cancel.refresh_buttons
    extra = handle_button(state, "custom_confirm", extra_confirm_button_ids={"custom_confirm"})
    assert extra.handled and extra.request_confirm
    unknown = handle_button(state, "unknown")
    assert not unknown.handled


def test_prompt_key_and_char_handling() -> None:
    state = open_prompt(title="Save", initial_value="ab", confirm_button_id="prompt_confirm")
    with_char = handle_char(state, "c")
    assert with_char.handled and with_char.state.buffer == "abc"
    backspace = handle_key(with_char.state, "backspace")
    assert backspace.handled and backspace.state.buffer == "ab"
    enter = handle_key(backspace.state, "enter")
    assert enter.handled and enter.request_confirm
    escape = handle_key(backspace.state, "escape")
    assert escape.handled and escape.state.prompt is None and escape.refresh_buttons
    unsupported = handle_key(backspace.state, "f1")
    assert not unsupported.handled


def test_prompt_rejects_invalid_char_and_handles_none_prompt() -> None:
    state = open_prompt(title="Save", initial_value="", confirm_button_id="prompt_confirm")
    assert not handle_char(state, "\n").handled
    assert not handle_char(state, "ab").handled
    full = open_prompt(title="Save", initial_value="x" * 32, confirm_button_id="prompt_confirm")
    assert not handle_char(full, "y").handled

    closed = close_prompt()
    assert not handle_key(closed, "enter").handled
    assert not handle_char(closed, "x").handled
    assert not handle_button(closed, "prompt_confirm").handled

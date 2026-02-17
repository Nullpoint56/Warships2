from __future__ import annotations

from engine.api.dialogs import DialogOpenSpec, open_dialog, resolve_confirm_button_id


def test_resolve_confirm_button_id_with_default() -> None:
    assert resolve_confirm_button_id("save", {"save": "ok_save"}, "ok_default") == "ok_save"
    assert resolve_confirm_button_id("unknown", {"save": "ok_save"}, "ok_default") == "ok_default"


def test_open_dialog_builds_prompt_state() -> None:
    state = open_dialog(
        DialogOpenSpec(
            title="Title",
            initial_value="value",
            mode="save",
            confirm_button_id="ok",
            cancel_button_id="cancel",
            target="x",
        )
    )
    assert state.prompt is not None
    assert state.prompt.confirm_button_id == "ok"
    assert state.prompt.cancel_button_id == "cancel"
    assert state.mode == "save"
    assert state.target == "x"


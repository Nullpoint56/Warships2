from warships.game.app.controller_state import ControllerState
from warships.game.app.ports.runtime_primitives import PromptInteractionOutcome, PromptState, PromptView
from warships.game.app.services.prompt_flow import PromptConfirmOutcome
from warships.game.app.services.prompt_orchestration import apply_prompt_confirm_outcome, apply_prompt_interaction_outcome
from warships.game.app.state_machine import AppState


def test_apply_prompt_interaction_outcome_paths() -> None:
    state = ControllerState()
    refreshed = {"count": 0}
    confirmed = {"count": 0}

    assert not apply_prompt_interaction_outcome(
        PromptInteractionOutcome(handled=False, state=PromptState()),
        state=state,
        confirm_prompt=lambda: False,
        refresh_buttons=lambda: None,
    )

    handled = apply_prompt_interaction_outcome(
        PromptInteractionOutcome(handled=True, state=PromptState(), request_confirm=True),
        state=state,
        confirm_prompt=lambda: confirmed.__setitem__("count", confirmed["count"] + 1) or True,
        refresh_buttons=lambda: refreshed.__setitem__("count", refreshed["count"] + 1),
    )
    assert handled
    assert confirmed["count"] == 1
    assert refreshed["count"] == 0

    handled_refresh = apply_prompt_interaction_outcome(
        PromptInteractionOutcome(handled=True, state=PromptState(), refresh_buttons=True),
        state=state,
        confirm_prompt=lambda: False,
        refresh_buttons=lambda: refreshed.__setitem__("count", refreshed["count"] + 1),
    )
    assert handled_refresh
    assert refreshed["count"] == 1


def test_apply_prompt_confirm_outcome_paths() -> None:
    state = ControllerState()
    calls = {"rows": 0, "buttons": 0, "announce": 0}
    assert not apply_prompt_confirm_outcome(
        PromptConfirmOutcome(
            handled=False,
            status=None,
            prompt=None,
            prompt_mode=None,
            prompt_target=None,
            prompt_buffer="",
            pending_save_name=None,
            editing_preset_name=None,
        ),
        state=state,
        refresh_preset_rows=lambda: None,
        refresh_buttons=lambda: None,
        announce_state=lambda: None,
    )

    outcome = PromptConfirmOutcome(
        handled=True,
        status="ok",
        prompt=PromptView("title", "value", "confirm", "cancel"),
        prompt_mode="save",
        prompt_target="x",
        prompt_buffer="buf",
        pending_save_name="p",
        editing_preset_name="e",
        switch_to_preset_manage=True,
        refresh_preset_rows=True,
        refresh_buttons=True,
        announce_state=True,
    )
    assert apply_prompt_confirm_outcome(
        outcome,
        state=state,
        refresh_preset_rows=lambda: calls.__setitem__("rows", calls["rows"] + 1),
        refresh_buttons=lambda: calls.__setitem__("buttons", calls["buttons"] + 1),
        announce_state=lambda: calls.__setitem__("announce", calls["announce"] + 1),
    )
    assert state.status == "ok"
    assert state.app_state is AppState.PRESET_MANAGE
    assert calls == {"rows": 1, "buttons": 1, "announce": 1}

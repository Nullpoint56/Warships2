from warships.game.app.services.prompt_flow import PromptFlowService
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_prompt_runtime_wrapper_methods() -> None:
    state = PromptFlowService.open_prompt("Save", "x", mode="save")
    assert state.prompt is not None
    synced = PromptFlowService.sync_prompt(state, "y")
    assert synced.buffer == "y"
    handled_key = PromptFlowService.handle_key(synced, "enter")
    assert handled_key.handled
    handled_char = PromptFlowService.handle_char(synced, "a")
    assert handled_char.handled
    handled_button = PromptFlowService.handle_button(synced, "prompt_cancel")
    assert handled_button.handled
    closed = PromptFlowService.close_prompt()
    assert closed.prompt is None


def test_prompt_confirm_failure_and_unhandled_paths(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    # rename failure
    rename_fail = PromptFlowService.confirm(
        mode="rename",
        value="new",
        prompt_target="missing",
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=[],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert rename_fail.handled
    assert rename_fail.status is not None and rename_fail.status.startswith("Rename failed:")

    # overwrite failure via invalid placements
    overwrite_fail = PromptFlowService.confirm(
        mode="overwrite",
        value="bad",
        prompt_target=None,
        pending_save_name="bad",
        editing_preset_name=None,
        preset_names=[],
        placements=[],
        preset_service=service,
    )
    assert overwrite_fail.handled
    assert overwrite_fail.status is not None and overwrite_fail.status.startswith("Save failed:")

    # unhandled generic path
    unhandled = PromptFlowService.confirm(
        mode="noop",
        value="x",
        prompt_target=None,
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=[],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert not unhandled.handled


def test_prompt_confirm_save_success_without_overwrite(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    outcome = PromptFlowService.confirm(
        mode="save",
        value="fresh",
        prompt_target=None,
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=[],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert outcome.handled
    assert outcome.status == "Saved preset 'fresh'."
    assert outcome.switch_to_preset_manage
    assert outcome.refresh_preset_rows


def test_prompt_confirm_save_failure_with_invalid_fleet(tmp_path) -> None:
    service = PresetService(PresetRepository(tmp_path))
    outcome = PromptFlowService.confirm(
        mode="save",
        value="bad",
        prompt_target=None,
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=[],
        placements=[],
        preset_service=service,
    )
    assert outcome.handled
    assert outcome.status is not None and outcome.status.startswith("Save failed:")

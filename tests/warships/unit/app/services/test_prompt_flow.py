from warships.game.app.services.prompt_flow import PromptFlowService
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_open_prompt_sets_mode_specific_confirm_button() -> None:
    save = PromptFlowService.open_prompt("Save", "x", mode="save")
    rename = PromptFlowService.open_prompt("Rename", "x", mode="rename")
    overwrite = PromptFlowService.open_prompt("Overwrite", "x", mode="overwrite")
    assert save.prompt is not None and save.prompt.confirm_button_id == "prompt_confirm_save"
    assert rename.prompt is not None and rename.prompt.confirm_button_id == "prompt_confirm_rename"
    assert overwrite.prompt is not None and overwrite.prompt.confirm_button_id == "prompt_confirm_overwrite"


def test_confirm_rejects_empty_name(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    outcome = PromptFlowService.confirm(
        mode="save",
        value="   ",
        prompt_target=None,
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=[],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert outcome.handled
    assert outcome.status == "Name cannot be empty."


def test_confirm_save_and_overwrite_flow(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("taken", valid_fleet)
    overwrite_prompt = PromptFlowService.confirm(
        mode="save",
        value="taken",
        prompt_target=None,
        pending_save_name=None,
        editing_preset_name="other",
        preset_names=["taken"],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert overwrite_prompt.handled
    assert overwrite_prompt.prompt is not None
    assert overwrite_prompt.prompt_mode == "overwrite"

    overwrite = PromptFlowService.confirm(
        mode="overwrite",
        value="taken",
        prompt_target=None,
        pending_save_name="taken",
        editing_preset_name="other",
        preset_names=["taken"],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert overwrite.handled
    assert "Overwrote preset 'taken'." == overwrite.status


def test_confirm_rename_success(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("old_name", valid_fleet)
    outcome = PromptFlowService.confirm(
        mode="rename",
        value="new_name",
        prompt_target="old_name",
        pending_save_name=None,
        editing_preset_name=None,
        preset_names=["old_name"],
        placements=list(valid_fleet.ships),
        preset_service=service,
    )
    assert outcome.handled
    assert outcome.status == "Renamed 'old_name' to 'new_name'."

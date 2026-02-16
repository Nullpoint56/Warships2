import logging

from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_refresh_rows_skips_invalid_payload_files(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("valid", valid_fleet)
    (tmp_path / "broken.json").write_text("{bad json", encoding="utf-8")
    result = PresetFlowService.refresh_rows(
        preset_service=service,
        selected_preset="valid",
        scroll=0,
        visible_rows=5,
        logger=logging.getLogger("test"),
    )
    assert [row.name for row in result.rows] == ["valid"]
    assert result.selected_preset == "valid"


def test_select_and_edit_preset_success_and_failure(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("alpha", valid_fleet)
    selected = PresetFlowService.select_new_game_preset(service, "alpha")
    assert selected.selected_preset == "alpha"
    assert selected.status == "Selected preset 'alpha'."

    missing = PresetFlowService.select_new_game_preset(service, "missing")
    assert missing.selected_preset is None
    assert "Failed to load preset" in missing.status

    edit_ok = PresetFlowService.load_preset_for_edit(service, "alpha")
    assert edit_ok.success
    edit_missing = PresetFlowService.load_preset_for_edit(service, "missing")
    assert not edit_missing.success

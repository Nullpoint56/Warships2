import random

from warships.game.app.services.new_game_flow import NewGameFlowService
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_choose_difficulty_valid_and_invalid() -> None:
    idx, status = NewGameFlowService.choose_difficulty(1, "Hard")
    assert idx == 2
    assert status == "Difficulty: Hard."
    same_idx, no_status = NewGameFlowService.choose_difficulty(1, "Impossible")
    assert same_idx == 1
    assert no_status is None


def test_default_selection_and_randomize_selection(valid_fleet) -> None:
    rows = []
    assert NewGameFlowService.default_selection(rows) is None
    selection = NewGameFlowService.randomize_selection(random.Random(1))
    assert selection.random_fleet is not None
    assert selection.source_label == "Random Fleet"
    assert len(selection.preview) == 5


def test_select_preset_success_and_failure(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("alpha", valid_fleet)
    ok = NewGameFlowService.select_preset(service, "alpha")
    assert ok.selected_preset == "alpha"
    assert ok.source_label == "Preset: alpha"

    missing = NewGameFlowService.select_preset(service, "missing")
    assert missing.selected_preset is None
    assert "Failed to load preset" in (missing.status or "")

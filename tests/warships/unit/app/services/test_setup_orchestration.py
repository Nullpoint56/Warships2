import logging

from warships.game.app.services.setup_orchestration import (
    refresh_preset_state,
    resolve_new_game_selection,
)
from warships.game.app.ui_state import PresetRowView
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_refresh_preset_state_clamps_scrolls(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("alpha", valid_fleet)
    state = refresh_preset_state(
        preset_service=service,
        selected_preset="missing",
        new_game_scroll=99,
        preset_manage_scroll=99,
        new_game_visible_rows=3,
        preset_manage_visible_rows=3,
        logger=logging.getLogger("test"),
    )
    assert len(state.rows) == 1
    assert state.selected_preset is None
    assert state.new_game_scroll == 0
    assert state.preset_manage_scroll == 0


def test_resolve_new_game_selection_default(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    none_case = resolve_new_game_selection(preset_service=service, preset_rows=[])
    assert none_case.selected_preset is None
    service.save_preset("alpha", valid_fleet)
    rows = [PresetRowView(name="alpha", placements=list(valid_fleet.ships))]
    selected = resolve_new_game_selection(preset_service=service, preset_rows=rows)
    assert selected.selected_preset == "alpha"
    assert selected.source_label == "Preset: alpha"

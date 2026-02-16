from __future__ import annotations

from warships.game.app.events import ButtonPressed
from warships.game.app.state_machine import AppState
from warships.game.ui.layout_metrics import PRESET_PANEL


def test_controller_initial_state_main_menu(controller_factory) -> None:
    controller = controller_factory()
    ui = controller.ui_state()
    assert ui.state is AppState.MAIN_MENU
    assert any(button.id == "new_game" for button in ui.buttons)


def test_controller_new_game_and_start_game_flow(controller_factory, preset_service, valid_fleet) -> None:
    preset_service.save_preset("alpha", valid_fleet)
    controller = controller_factory()
    assert controller.handle_button(ButtonPressed("new_game"))
    assert controller.ui_state().state is AppState.NEW_GAME_SETUP
    assert controller.handle_button(ButtonPressed("start_game"))
    ui = controller.ui_state()
    assert ui.state is AppState.BATTLE
    assert ui.session is not None


def test_controller_manage_presets_and_wheel_scroll(controller_factory, preset_service, valid_fleet) -> None:
    for idx in range(12):
        preset_service.save_preset(f"preset_{idx:02d}", valid_fleet)
    controller = controller_factory()
    controller.handle_button(ButtonPressed("manage_presets"))
    ui_before = controller.ui_state()
    first_before = ui_before.preset_rows[0].name if ui_before.preset_rows else None
    panel = PRESET_PANEL.panel_rect()
    handled = controller.handle_wheel(panel.x + 5.0, panel.y + 5.0, 1.0)
    ui_after = controller.ui_state()
    first_after = ui_after.preset_rows[0].name if ui_after.preset_rows else None
    assert handled
    assert first_before != first_after


def test_controller_create_preset_save_requires_full_placement(controller_factory) -> None:
    controller = controller_factory()
    controller.handle_button(ButtonPressed("create_preset"))
    assert controller.ui_state().state is AppState.PLACEMENT_EDIT
    controller.handle_button(ButtonPressed("save_preset"))
    assert "Place all ships before saving." == controller.ui_state().status

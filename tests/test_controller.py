"""Controller-level state transition tests."""

from __future__ import annotations

import random
from pathlib import Path

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed
from warships.app.state_machine import AppState
from warships.core.models import Coord
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService


def _controller(tmp_path: Path) -> GameController:
    service = PresetService(PresetRepository(tmp_path))
    return GameController(preset_service=service, rng=random.Random(123))


def test_main_menu_to_placement(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    assert controller.ui_state().state is AppState.MAIN_MENU

    changed = controller.handle_button(ButtonPressed("new_game"))

    ui = controller.ui_state()
    assert changed is True
    assert ui.state is AppState.PLACEMENT_EDIT
    assert "Placement" in ui.status


def test_randomize_enables_start_battle(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    controller.handle_button(ButtonPressed("new_game"))

    controller.handle_button(ButtonPressed("randomize"))
    ui = controller.ui_state()
    start_button = next(button for button in ui.buttons if button.id == "start_battle")
    assert start_button.enabled is True


def test_battle_shot_changes_status(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    controller.handle_button(ButtonPressed("new_game"))
    controller.handle_button(ButtonPressed("randomize"))
    controller.handle_button(ButtonPressed("start_battle"))

    ui = controller.ui_state()
    assert ui.state is AppState.BATTLE

    changed = controller.handle_board_click(BoardCellPressed(is_ai_board=True, coord=Coord(0, 0)))

    assert changed is True
    assert controller.ui_state().status != "Battle started. Click enemy board to fire."

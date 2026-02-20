from __future__ import annotations

from dataclasses import replace

from engine.ui_runtime.grid_layout import GridLayout
from tests.warships.unit.ui.helpers import FakeRenderer, make_ui_state
from warships.game.app.state_machine import AppState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.core.rules import create_session
from warships.game.ui.game_view import GameView


def _snapshot_command_keys(snapshot) -> set[str]:
    keys: set[str] = set()
    for render_pass in snapshot.passes:
        for command in render_pass.commands:
            payload = {str(k): v for k, v in command.data}
            key = payload.get("key")
            if isinstance(key, str):
                keys.add(key)
    return keys


def _snapshot_kind_counts(snapshot) -> dict[str, int]:
    counts: dict[str, int] = {}
    for render_pass in snapshot.passes:
        for command in render_pass.commands:
            kind = str(command.kind)
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def test_main_menu_snapshot_contains_background_and_buttons() -> None:
    view = GameView(FakeRenderer(), GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)

    snapshot, _labels = view.build_snapshot(
        frame_index=1,
        ui=ui,
        debug_ui=False,
        debug_labels_state=[],
    )

    counts = _snapshot_kind_counts(snapshot)
    keys = _snapshot_command_keys(snapshot)
    assert counts.get("fill_window", 0) >= 1
    assert any(key.startswith("button:bg:") for key in keys)
    assert any(key.startswith("button:text:") for key in keys)


def test_placement_snapshot_contains_grid_ships_and_status_overlay() -> None:
    view = GameView(FakeRenderer(), GridLayout())
    ui = make_ui_state(state=AppState.PLACEMENT_EDIT)
    ui = replace(
        ui,
        status="Placement mode",
        placements=[ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)],
    )

    snapshot, _labels = view.build_snapshot(
        frame_index=2,
        ui=ui,
        debug_ui=False,
        debug_labels_state=[],
    )

    keys = _snapshot_command_keys(snapshot)
    assert "board:grid:player" in keys
    assert "placement:panel" in keys
    assert any(key.startswith("ship:placement:") for key in keys)
    assert "status:bg" in keys
    assert "title:player" in keys


def test_battle_snapshot_contains_hit_miss_and_enemy_overlay(valid_fleet) -> None:
    view = GameView(FakeRenderer(), GridLayout())
    session = create_session(valid_fleet, valid_fleet)
    session.player_board.apply_shot(Coord(0, 0))
    session.player_board.apply_shot(Coord(9, 9))
    session.ai_board.apply_shot(Coord(0, 0))
    session.ai_board.apply_shot(Coord(9, 9))
    ui = make_ui_state(state=AppState.BATTLE)
    ui = replace(ui, status="Battle mode", session=session)

    snapshot, _labels = view.build_snapshot(
        frame_index=3,
        ui=ui,
        debug_ui=False,
        debug_labels_state=[],
    )

    keys = _snapshot_command_keys(snapshot)
    assert "board:grid:player" in keys
    assert "board:grid:ai" in keys
    assert any(key.startswith("shot:player:") for key in keys)
    assert any(key.startswith("shot:ai:") for key in keys)
    assert "title:enemy" in keys

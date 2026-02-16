from warships.game.app.controller_state import ControllerState
from warships.game.app.services.battle import PlayerTurnResult
from warships.game.app.services.mutation_orchestration import (
    apply_battle_turn_outcome,
    apply_edit_preset_result,
    apply_placement_outcome,
)
from warships.game.app.services.placement_flow import HeldShipState, PlacementActionResult
from warships.game.app.services.preset_flow import EditPresetResult
from warships.game.app.state_machine import AppState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType, ShotResult, Turn


def test_apply_placement_outcome_paths() -> None:
    state = ControllerState()
    refreshed = {"count": 0}

    def refresh_buttons() -> None:
        refreshed["count"] += 1

    not_handled = apply_placement_outcome(
        PlacementActionResult(False, HeldShipState(None, None, None, 0)),
        state=state,
        refresh_buttons=refresh_buttons,
    )
    assert not not_handled

    handled = apply_placement_outcome(
        PlacementActionResult(
            True,
            HeldShipState(ShipType.DESTROYER, Orientation.HORIZONTAL, None, 1),
            status="ok",
            refresh_buttons=True,
        ),
        state=state,
        refresh_buttons=refresh_buttons,
    )
    assert handled
    assert state.status == "ok"
    assert refreshed["count"] == 1


def test_apply_battle_turn_outcome_sets_result_state_on_winner() -> None:
    state = ControllerState()
    refreshed = {"count": 0}
    apply_battle_turn_outcome(
        PlayerTurnResult(shot_result=ShotResult.MISS, status="x", winner=Turn.PLAYER),
        state=state,
        refresh_buttons=lambda: refreshed.__setitem__("count", refreshed["count"] + 1),
    )
    assert state.app_state is AppState.RESULT
    assert refreshed["count"] == 1


def test_apply_edit_preset_result_paths() -> None:
    state = ControllerState()
    calls = {"reset": 0, "apply": 0, "refresh": 0, "announce": 0}

    def reset_editor() -> None:
        calls["reset"] += 1

    def apply_placements(items: list[ShipPlacement]) -> None:
        _ = items
        calls["apply"] += 1

    def refresh_buttons() -> None:
        calls["refresh"] += 1

    def announce_state() -> None:
        calls["announce"] += 1

    fail = apply_edit_preset_result(
        EditPresetResult(placements=[], status="fail", success=False),
        preset_name="p",
        state=state,
        reset_editor=reset_editor,
        apply_placements=apply_placements,
        refresh_buttons=refresh_buttons,
        announce_state=announce_state,
    )
    assert fail
    assert state.status == "fail"

    ok = apply_edit_preset_result(
        EditPresetResult(
            placements=[ShipPlacement(ShipType.DESTROYER, Coord(0, 0), Orientation.HORIZONTAL)],
            status="ok",
            success=True,
        ),
        preset_name="p",
        state=state,
        reset_editor=reset_editor,
        apply_placements=apply_placements,
        refresh_buttons=refresh_buttons,
        announce_state=announce_state,
    )
    assert ok
    assert state.app_state is AppState.PLACEMENT_EDIT
    assert (
        calls["reset"] == 1
        and calls["apply"] == 1
        and calls["refresh"] == 1
        and calls["announce"] == 1
    )

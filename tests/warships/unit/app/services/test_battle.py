import random

import warships.game.app.services.battle as battle_service
from warships.game.app.services.battle import build_ai_strategy, resolve_player_turn, start_game
from warships.game.core.models import Coord, ShotResult, Turn
from warships.game.core.rules import create_session
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_start_game_requires_selection(tmp_path) -> None:
    service = PresetService(PresetRepository(tmp_path))
    result = start_game(
        preset_service=service,
        rng=random.Random(1),
        difficulty="Normal",
        selected_preset=None,
        random_fleet_choice=None,
    )
    assert not result.success
    assert result.session is None


def test_start_game_with_preset_and_missing_preset(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("alpha", valid_fleet)
    ok = start_game(
        preset_service=service,
        rng=random.Random(2),
        difficulty="Easy",
        selected_preset="alpha",
        random_fleet_choice=None,
    )
    assert ok.success
    assert ok.session is not None
    assert ok.ai_strategy is not None

    missing = start_game(
        preset_service=service,
        rng=random.Random(2),
        difficulty="Easy",
        selected_preset="missing",
        random_fleet_choice=None,
    )
    assert not missing.success


def test_resolve_player_turn_invalid_and_regular_paths(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    ai = build_ai_strategy("Easy", random.Random(3))
    invalid = resolve_player_turn(session, ai, Coord(-1, 0))
    assert invalid.shot_result is ShotResult.INVALID

    session.turn = Turn.PLAYER
    regular = resolve_player_turn(session, ai, Coord(9, 9))
    assert regular.shot_result in {ShotResult.MISS, ShotResult.HIT, ShotResult.SUNK}


def test_build_ai_strategy_defaults_unknown_difficulty_to_normal() -> None:
    ai = build_ai_strategy("Impossible", random.Random(4))
    # "Normal" maps to hunt-target.
    assert ai.__class__.__name__ == "HuntTargetAI"


def test_resolve_player_turn_keeps_player_sink_feedback_when_ai_responds(monkeypatch) -> None:
    session = create_session(_fleet_for_test(), _fleet_for_test())

    def _fake_player_fire(session_obj, coord):
        _ = coord
        session_obj.last_message = "You fired at (2, 3): sunk DESTROYER."
        session_obj.turn = Turn.AI
        return ShotResult.SUNK

    def _fake_ai_turn(session_obj, ai_strategy):
        _ = ai_strategy
        session_obj.last_message = "AI fired at (4, 4): miss."
        session_obj.turn = Turn.PLAYER

    monkeypatch.setattr(battle_service, "player_fire", _fake_player_fire)
    monkeypatch.setattr(battle_service, "_run_ai_turn", _fake_ai_turn)

    result = resolve_player_turn(session, build_ai_strategy("Easy", random.Random(9)), Coord(2, 3))
    assert result.shot_result is ShotResult.SUNK
    assert "sunk DESTROYER" in result.status
    assert "AI fired at (4, 4): miss." in result.status


def _fleet_for_test():
    from warships.game.core.models import Coord as _Coord
    from warships.game.core.models import FleetPlacement, Orientation, ShipPlacement, ShipType

    return FleetPlacement(
        ships=[
            ShipPlacement(ShipType.CARRIER, _Coord(0, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.BATTLESHIP, _Coord(2, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CRUISER, _Coord(4, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.SUBMARINE, _Coord(6, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.DESTROYER, _Coord(8, 0), Orientation.HORIZONTAL),
        ]
    )

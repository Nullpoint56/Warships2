import random

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

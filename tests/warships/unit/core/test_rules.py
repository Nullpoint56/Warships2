from warships.game.core.models import Coord, ShotResult, Turn, cells_for_placement
from warships.game.core.rules import ai_fire, create_session, player_fire


def test_create_session_defaults(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    assert session.turn is Turn.PLAYER
    assert session.winner is None


def test_player_fire_turn_and_repeat_behavior(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    result = player_fire(session, Coord(9, 9))
    assert result is ShotResult.MISS
    assert session.turn is Turn.AI
    assert player_fire(session, Coord(9, 8)) is ShotResult.INVALID


def test_ai_fire_respects_turn(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    assert ai_fire(session, Coord(0, 0)) is ShotResult.INVALID
    session.turn = Turn.AI
    result = ai_fire(session, Coord(9, 9))
    assert result is ShotResult.MISS
    assert session.turn is Turn.PLAYER


def test_player_can_win_after_all_enemy_cells_hit(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    for placement in valid_fleet.ships:
        for cell in cells_for_placement(placement):
            session.turn = Turn.PLAYER
            player_fire(session, cell)
    assert session.winner is Turn.PLAYER

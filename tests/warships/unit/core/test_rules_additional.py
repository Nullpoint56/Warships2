from warships.game.core.models import Coord, ShotResult, Turn, cells_for_placement
from warships.game.core.rules import ai_fire, create_session, player_fire


def test_repeat_and_invalid_paths(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    session.turn = Turn.PLAYER
    assert player_fire(session, Coord(-1, 0)) is ShotResult.INVALID
    first = player_fire(session, Coord(9, 9))
    assert first in {ShotResult.MISS, ShotResult.HIT, ShotResult.SUNK}
    session.turn = Turn.PLAYER
    assert player_fire(session, Coord(9, 9)) is ShotResult.REPEAT


def test_ai_wins_path(valid_fleet) -> None:
    session = create_session(valid_fleet, valid_fleet)
    for placement in valid_fleet.ships:
        for cell in cells_for_placement(placement):
            session.turn = Turn.AI
            ai_fire(session, cell)
    assert session.winner is Turn.AI
    assert session.last_message == "AI wins."

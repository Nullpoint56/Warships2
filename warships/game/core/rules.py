"""Rule validation and turn resolution logic."""

from __future__ import annotations

from dataclasses import dataclass, field

from warships.game.core.board import BoardState
from warships.game.core.fleet import build_board_from_fleet
from warships.game.core.models import Coord, FleetPlacement, ShotResult, Turn


@dataclass(slots=True)
class GameSession:
    """Runtime game session state."""

    player_board: BoardState
    ai_board: BoardState
    turn: Turn = Turn.PLAYER
    winner: Turn | None = None
    last_message: str = "Place your fleet."
    history: list[str] = field(default_factory=list)


def create_session(player_fleet: FleetPlacement, ai_fleet: FleetPlacement) -> GameSession:
    """Create a game session from fleet placements."""
    player_board = build_board_from_fleet(player_fleet)
    ai_board = build_board_from_fleet(ai_fleet)
    return GameSession(
        player_board=player_board,
        ai_board=ai_board,
        turn=Turn.PLAYER,
        last_message="Battle started. Your turn.",
    )


def player_fire(session: GameSession, coord: Coord) -> ShotResult:
    """Resolve player shot at the AI board."""
    if session.winner is not None:
        return ShotResult.INVALID
    if session.turn is not Turn.PLAYER:
        return ShotResult.INVALID

    result, sunk_type = session.ai_board.apply_shot(coord)
    if result in (ShotResult.INVALID, ShotResult.REPEAT):
        return result

    if result is ShotResult.MISS:
        session.last_message = f"You fired at ({coord.row}, {coord.col}): miss."
        session.turn = Turn.AI
    elif result is ShotResult.HIT:
        session.last_message = f"You fired at ({coord.row}, {coord.col}): hit."
        session.turn = Turn.AI
    else:
        session.last_message = (
            f"You fired at ({coord.row}, {coord.col}): sunk {sunk_type.value if sunk_type else 'ship'}."
        )
        session.turn = Turn.AI

    session.history.append(session.last_message)
    if session.ai_board.all_ships_sunk():
        session.winner = Turn.PLAYER
        session.turn = Turn.PLAYER
        session.last_message = "You win."
        session.history.append(session.last_message)
    return result


def ai_fire(session: GameSession, coord: Coord) -> ShotResult:
    """Resolve AI shot at the player board."""
    if session.winner is not None:
        return ShotResult.INVALID
    if session.turn is not Turn.AI:
        return ShotResult.INVALID

    result, sunk_type = session.player_board.apply_shot(coord)
    if result in (ShotResult.INVALID, ShotResult.REPEAT):
        return result

    if result is ShotResult.MISS:
        session.last_message = f"AI fired at ({coord.row}, {coord.col}): miss."
        session.turn = Turn.PLAYER
    elif result is ShotResult.HIT:
        session.last_message = f"AI fired at ({coord.row}, {coord.col}): hit."
        session.turn = Turn.PLAYER
    else:
        session.last_message = (
            f"AI fired at ({coord.row}, {coord.col}): sunk {sunk_type.value if sunk_type else 'ship'}."
        )
        session.turn = Turn.PLAYER

    session.history.append(session.last_message)
    if session.player_board.all_ships_sunk():
        session.winner = Turn.AI
        session.turn = Turn.AI
        session.last_message = "AI wins."
        session.history.append(session.last_message)
    return result


"""Battle flow orchestration separated from UI controller logic."""

from __future__ import annotations

from dataclasses import dataclass
import random

from warships.ai.hunt_target import HuntTargetAI
from warships.ai.strategy import AIStrategy
from warships.core.fleet import random_fleet
from warships.core.models import Coord, FleetPlacement, ShotResult, Turn
from warships.core.rules import GameSession, ai_fire, create_session, player_fire
from warships.presets.service import PresetService


@dataclass(frozen=True, slots=True)
class StartGameResult:
    """Outcome of starting a new game session."""

    session: GameSession | None
    ai_strategy: AIStrategy | None
    status: str
    success: bool


@dataclass(frozen=True, slots=True)
class PlayerTurnResult:
    """Outcome of a full player action (player shot + optional AI response)."""

    shot_result: ShotResult
    status: str
    winner: Turn | None


def start_game(
    *,
    preset_service: PresetService,
    rng: random.Random,
    difficulty: str,
    selected_preset: str | None,
    random_fleet_choice: FleetPlacement | None,
) -> StartGameResult:
    """Create a new session and AI strategy from setup choices."""
    if random_fleet_choice is not None:
        player_fleet = random_fleet_choice
        source_label = "Random Fleet"
    elif selected_preset is not None:
        try:
            player_fleet = preset_service.load_preset(selected_preset)
        except (ValueError, FileNotFoundError) as exc:
            return StartGameResult(
                session=None,
                ai_strategy=None,
                status=f"Failed to load preset '{selected_preset}': {exc}",
                success=False,
            )
        source_label = f"Preset: {selected_preset}"
    else:
        return StartGameResult(
            session=None,
            ai_strategy=None,
            status="Select a preset or generate a random fleet first.",
            success=False,
        )

    session = create_session(player_fleet, random_fleet(rng))
    strategy = build_ai_strategy(difficulty, rng)
    return StartGameResult(
        session=session,
        ai_strategy=strategy,
        status=f"Game started ({difficulty}) using {source_label}.",
        success=True,
    )


def resolve_player_turn(session: GameSession, ai_strategy: AIStrategy, coord: Coord) -> PlayerTurnResult:
    """Apply player shot and resolve AI response when needed."""
    result = player_fire(session, coord)
    if result in {ShotResult.INVALID, ShotResult.REPEAT}:
        return PlayerTurnResult(shot_result=result, status="Invalid target. Choose another enemy cell.", winner=session.winner)

    if session.winner is not None:
        return PlayerTurnResult(shot_result=result, status=session.last_message, winner=session.winner)

    _run_ai_turn(session, ai_strategy)
    return PlayerTurnResult(shot_result=result, status=session.last_message, winner=session.winner)


def _run_ai_turn(session: GameSession, ai_strategy: AIStrategy) -> None:
    if session.turn is not Turn.AI or session.winner is not None:
        return
    for _ in range(200):
        shot = ai_strategy.choose_shot()
        result = ai_fire(session, shot)
        if result in {ShotResult.INVALID, ShotResult.REPEAT}:
            continue
        ai_strategy.notify_result(shot, result)
        break


def build_ai_strategy(difficulty: str, rng: random.Random) -> AIStrategy:
    """Construct AI strategy from selected difficulty."""
    if difficulty == "Easy":
        return _RandomShotAI(rng)
    if difficulty == "Hard":
        return HuntTargetAI(rng)
    return HuntTargetAI(rng)


class _RandomShotAI(AIStrategy):
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._remaining: set[tuple[int, int]] = {(r, c) for r in range(10) for c in range(10)}

    def choose_shot(self) -> Coord:
        row, col = self._rng.choice(list(self._remaining))
        return Coord(row=row, col=col)

    def notify_result(self, coord: Coord, result: ShotResult) -> None:
        self._remaining.discard((coord.row, coord.col))

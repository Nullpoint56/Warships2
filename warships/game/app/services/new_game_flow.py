"""New-game setup flow helpers extracted from controller."""

from __future__ import annotations

from dataclasses import dataclass
import random

from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.app.ui_state import PresetRowView
from warships.game.core.fleet import random_fleet
from warships.game.core.models import FleetPlacement, ShipPlacement
from warships.game.presets.service import PresetService

DIFFICULTIES: tuple[str, ...] = ("Easy", "Normal", "Hard")


@dataclass(frozen=True, slots=True)
class NewGameSelection:
    """Current new-game fleet source/preview selection."""

    selected_preset: str | None
    random_fleet: FleetPlacement | None
    preview: list[ShipPlacement]
    source_label: str | None
    status: str | None = None


class NewGameFlowService:
    """State transition helpers for new-game setup."""

    @staticmethod
    def current_difficulty(index: int) -> str:
        return DIFFICULTIES[index]

    @staticmethod
    def choose_difficulty(current_index: int, option: str) -> tuple[int, str | None]:
        if option not in DIFFICULTIES:
            return current_index, None
        new_index = DIFFICULTIES.index(option)
        return new_index, f"Difficulty: {DIFFICULTIES[new_index]}."

    @staticmethod
    def default_selection(rows: list[PresetRowView]) -> str | None:
        if not rows:
            return None
        return rows[0].name

    @staticmethod
    def select_preset(preset_service: PresetService, name: str) -> NewGameSelection:
        result = PresetFlowService.select_new_game_preset(preset_service, name)
        return NewGameSelection(
            selected_preset=result.selected_preset,
            random_fleet=result.random_fleet,
            preview=result.preview,
            source_label=result.source_label,
            status=result.status,
        )

    @staticmethod
    def randomize_selection(rng: random.Random) -> NewGameSelection:
        fleet = random_fleet(rng)
        return NewGameSelection(
            selected_preset=None,
            random_fleet=fleet,
            preview=list(fleet.ships),
            source_label="Random Fleet",
            status="Generated random fleet for this game.",
        )



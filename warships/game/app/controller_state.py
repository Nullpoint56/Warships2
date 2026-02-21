"""Mutable controller state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.api.screens import ScreenStack, create_screen_stack
from warships.game.ai.strategy import AIStrategy
from warships.game.app.ports.runtime_primitives import Button, PromptState
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import PresetRowView
from warships.game.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType
from warships.game.core.rules import GameSession


@dataclass(slots=True)
class ControllerState:
    """Aggregates all mutable state owned by GameController."""

    app_state: AppState = AppState.MAIN_MENU
    screen_stack: ScreenStack = field(default_factory=create_screen_stack)
    status: str = "Choose New Game, Manage Presets, or Quit."
    is_closing: bool = False
    session: GameSession | None = None
    ai_strategy: AIStrategy | None = None

    placements_by_type: dict[ShipType, ShipPlacement | None] = field(default_factory=dict)
    held_ship_type: ShipType | None = None
    held_orientation: Orientation | None = None
    held_previous: ShipPlacement | None = None
    held_grab_index: int = 0
    hover_cell: Coord | None = None
    hover_x: float | None = None
    hover_y: float | None = None
    held_preview_valid: bool = True
    held_preview_reason: str | None = None
    placement_popup_message: str | None = None

    preset_rows: list[PresetRowView] = field(default_factory=list)
    preset_manage_scroll: int = 0
    editing_preset_name: str | None = None
    new_game_difficulty_index: int = 1
    new_game_difficulty_open: bool = False
    new_game_selected_preset: str | None = None
    new_game_preset_scroll: int = 0
    new_game_random_fleet: FleetPlacement | None = None
    new_game_preview: list[ShipPlacement] = field(default_factory=list)
    new_game_source_label: str | None = None

    prompt_state: PromptState = field(default_factory=PromptState)
    pending_save_name: str | None = None

    buttons: list[Button] = field(default_factory=list)

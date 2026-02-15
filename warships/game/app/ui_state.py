"""Typed UI state exposed by the controller."""

from __future__ import annotations

from dataclasses import dataclass

from warships.game.app.state_machine import AppState
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.core.rules import GameSession
from engine.ui_runtime.widgets import Button


@dataclass(frozen=True, slots=True)
class PresetRowView:
    """Preset management row."""

    name: str
    placements: list[ShipPlacement]


@dataclass(frozen=True, slots=True)
class TextPromptView:
    """Text prompt overlay state."""

    title: str
    value: str
    confirm_button_id: str
    cancel_button_id: str


@dataclass(frozen=True, slots=True)
class AppUIState:
    """View-ready state snapshot."""

    state: AppState
    status: str
    buttons: list[Button]
    placements: list[ShipPlacement]
    placement_orientation: Orientation
    session: GameSession | None
    ship_order: list[ShipType]
    is_closing: bool
    preset_rows: list[PresetRowView]
    prompt: TextPromptView | None
    held_ship_type: ShipType | None
    held_ship_orientation: Orientation | None
    held_grab_index: int
    hover_cell: Coord | None
    hover_x: float | None
    hover_y: float | None
    new_game_difficulty: str | None
    new_game_difficulty_open: bool
    new_game_difficulty_options: list[str]
    new_game_visible_presets: list[str]
    new_game_selected_preset: str | None
    new_game_can_scroll_up: bool
    new_game_can_scroll_down: bool
    new_game_source: str | None
    new_game_preview: list[ShipPlacement]
    preset_manage_can_scroll_up: bool = False
    preset_manage_can_scroll_down: bool = False


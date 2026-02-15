"""Typed UI state exposed by the controller."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.state_machine import AppState
from warships.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.core.rules import GameSession
from warships.ui.overlays import Button


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

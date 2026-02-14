"""Typed UI state exposed by the controller."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.state_machine import AppState
from warships.core.models import Orientation, ShipPlacement, ShipType
from warships.core.rules import GameSession
from warships.ui.overlays import Button


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

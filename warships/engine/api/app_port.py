"""Engine-facing application port contract."""

from __future__ import annotations

from typing import Protocol

from warships.app.ui_state import AppUIState
from warships.core.models import Coord


class EngineAppPort(Protocol):
    """Contract the engine runtime uses to talk to app-specific logic."""

    def ui_state(self) -> AppUIState:
        """Return current app UI snapshot."""

    def on_button(self, button_id: str) -> bool:
        """Handle UI button action."""

    def on_board_click(self, is_ai_board: bool, coord: Coord) -> bool:
        """Handle board click action."""

    def on_pointer_move(self, x: float, y: float) -> bool:
        """Handle pointer move."""

    def on_pointer_release(self, x: float, y: float, button: int) -> bool:
        """Handle pointer release."""

    def on_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Handle pointer down."""

    def on_key(self, key: str) -> bool:
        """Handle normalized key press."""

    def on_char(self, value: str) -> bool:
        """Handle character input."""

    def on_wheel(self, x: float, y: float, dy: float) -> bool:
        """Handle wheel input."""


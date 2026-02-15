"""Engine-facing application port contract."""

from __future__ import annotations

from typing import Protocol


class RectView(Protocol):
    """Minimal rectangle contract for hit-testing in runtime helpers."""

    def contains(self, px: float, py: float) -> bool:
        """Return whether a point is inside the rectangle."""


class ButtonView(Protocol):
    """Minimal button contract for interaction routing."""

    id: str
    enabled: bool

    def contains(self, px: float, py: float) -> bool:
        """Return whether a point is inside the button."""


class InteractionPlanView(Protocol):
    """Interaction plan contract consumed by engine runtime routing."""

    buttons: tuple[ButtonView, ...]
    shortcut_buttons: dict[str, str]
    allows_ai_board_click: bool
    wheel_scroll_in_new_game_list: bool
    wheel_scroll_in_preset_manage_panel: bool
    new_game_list_rect: RectView | None
    preset_manage_rect: RectView | None


class ModalWidgetView(Protocol):
    """Modal widget contract consumed by engine modal runtime routing."""

    confirm_button_id: str
    cancel_button_id: str
    confirm_button_rect: RectView
    cancel_button_rect: RectView
    input_rect: RectView
    panel_rect: RectView
    overlay_rect: RectView


class EngineAppPort(Protocol):
    """Contract the engine runtime uses to talk to app-specific logic."""

    def ui_state(self) -> object:
        """Return current app UI snapshot."""

    def modal_widget(self) -> ModalWidgetView | None:
        """Return modal widget view-model for runtime input routing."""

    def interaction_plan(self) -> InteractionPlanView:
        """Return interaction plan view-model for runtime input routing."""

    def on_button(self, button_id: str) -> bool:
        """Handle UI button action."""

    def on_board_click(self, is_ai_board: bool, row: int, col: int) -> bool:
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

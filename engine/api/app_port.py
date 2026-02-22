"""Engine-facing application port contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


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
    cell_click_surface: str | None
    wheel_scroll_regions: tuple[RectView, ...]


class ModalWidgetView(Protocol):
    """Modal widget contract consumed by engine modal runtime routing."""

    confirm_button_id: str
    cancel_button_id: str
    confirm_button_rect: RectView
    cancel_button_rect: RectView
    input_rect: RectView
    panel_rect: RectView
    overlay_rect: RectView


class EngineAppPort(ABC):
    """Contract the engine runtime uses to talk to app-specific logic."""

    @abstractmethod
    def ui_state(self) -> "UIStateView":
        """Return current app UI snapshot."""

    @abstractmethod
    def modal_widget(self) -> ModalWidgetView | None:
        """Return modal widget view-model for runtime input routing."""

    @abstractmethod
    def interaction_plan(self) -> InteractionPlanView:
        """Return interaction plan view-model for runtime input routing."""

    @abstractmethod
    def on_button(self, button_id: str) -> bool:
        """Handle UI button action."""

    @abstractmethod
    def on_cell_click(self, surface_target: str, row: int, col: int) -> bool:
        """Handle cell click action for a named surface target."""

    @abstractmethod
    def on_pointer_move(self, x: float, y: float) -> bool:
        """Handle pointer move."""

    @abstractmethod
    def on_pointer_release(self, x: float, y: float, button: int) -> bool:
        """Handle pointer release."""

    @abstractmethod
    def on_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Handle pointer down."""

    @abstractmethod
    def on_key(self, key: str) -> bool:
        """Handle normalized key press."""

    @abstractmethod
    def on_char(self, value: str) -> bool:
        """Handle character input."""

    @abstractmethod
    def on_wheel(self, x: float, y: float, dy: float) -> bool:
        """Handle wheel input."""


class UIStateView(Protocol):
    """Opaque app UI-state view contract."""


@runtime_checkable
class UIDesignResolutionProvider(Protocol):
    """Optional app capability: authored UI design resolution provider."""

    def ui_design_resolution(self) -> tuple[float, float]:
        """Return authored UI design resolution as width/height."""

"""Public UI framework routing API."""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import InputSnapshot


class UIFramework(ABC):
    """Input-routing framework contract used by game modules."""

    @abstractmethod
    def sync_ui_state(self) -> None:
        """Sync runtime state from app snapshot."""

    @abstractmethod
    def handle_pointer_event(self, event: PointerEvent) -> bool:
        """Handle pointer event and return changed flag."""

    @abstractmethod
    def handle_key_event(self, event: KeyEvent) -> bool:
        """Handle key/char event and return changed flag."""

    @abstractmethod
    def handle_wheel_event(self, event: WheelEvent) -> bool:
        """Handle wheel event and return changed flag."""

    @abstractmethod
    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        """Handle one immutable input snapshot and return changed flag."""

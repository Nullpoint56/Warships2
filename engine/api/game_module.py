"""Engine-hosted game module contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent


@dataclass(frozen=True, slots=True)
class HostFrameContext:
    """Per-frame context passed from engine host to game module."""

    frame_index: int


class HostControl(Protocol):
    """Host control surface exposed to game modules."""

    def request_redraw(self) -> None:
        """Schedule one redraw."""

    def close(self) -> None:
        """Request host shutdown."""


class GameModule(Protocol):
    """Engine-facing game module lifecycle and event hooks."""

    def on_start(self, host: HostControl) -> None:
        """Initialize game module and capture host control if needed."""

    def on_pointer_event(self, event: PointerEvent) -> bool:
        """Handle pointer event. Return whether state changed."""

    def on_key_event(self, event: KeyEvent) -> bool:
        """Handle key/char event. Return whether state changed."""

    def on_wheel_event(self, event: WheelEvent) -> bool:
        """Handle wheel event. Return whether state changed."""

    def on_frame(self, context: HostFrameContext) -> None:
        """Render/update one frame."""

    def should_close(self) -> bool:
        """Return whether host should stop."""

    def on_shutdown(self) -> None:
        """Release resources and finalize state."""


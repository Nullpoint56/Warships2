"""Public UI framework routing API."""

from __future__ import annotations

from typing import Protocol

from engine.api.app_port import EngineAppPort
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import InputSnapshot
from engine.api.render import RenderAPI
from engine.api.ui_primitives import GridLayout


class UIFramework(Protocol):
    """Input-routing framework contract used by game modules."""

    def sync_ui_state(self) -> None:
        """Sync runtime state from app snapshot."""

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        """Handle pointer event and return changed flag."""

    def handle_key_event(self, event: KeyEvent) -> bool:
        """Handle key/char event and return changed flag."""

    def handle_wheel_event(self, event: WheelEvent) -> bool:
        """Handle wheel event and return changed flag."""

    def handle_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        """Handle one immutable input snapshot and return changed flag."""


def create_ui_framework(
    *,
    app: EngineAppPort,
    renderer: RenderAPI,
    layout: GridLayout,
) -> UIFramework:
    """Create default UI framework implementation."""
    from engine.runtime.framework_engine import EngineUIFramework

    return EngineUIFramework(app=app, renderer=renderer, layout=layout)

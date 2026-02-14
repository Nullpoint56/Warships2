"""Mouse input mapping to placement and firing actions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import os
from typing import Any
from typing import Callable


@dataclass(frozen=True, slots=True)
class PointerClick:
    """Captured pointer click event."""

    x: float
    y: float
    button: int

logger = logging.getLogger(__name__)


class InputController:
    """Collect pointer events from canvas for polling by app loop."""

    def __init__(self, on_click_queued: Callable[[], None] | None = None) -> None:
        self._clicks: deque[PointerClick] = deque()
        self._debug = os.getenv("WARSHIPS_DEBUG_INPUT", "0") == "1"
        self._on_click_queued = on_click_queued

    def bind(self, canvas: Any) -> None:
        """Attach pointer listeners to a wgpu canvas."""
        if not hasattr(canvas, "add_event_handler"):
            raise RuntimeError("Canvas does not support event handlers.")
        canvas.add_event_handler(self._on_pointer_down, "pointer_down")
        if self._debug:
            canvas.add_event_handler(self._on_any_event, "*")

    def drain_clicks(self) -> list[PointerClick]:
        """Return and clear all queued clicks."""
        items = list(self._clicks)
        self._clicks.clear()
        return items

    def _on_pointer_down(self, event: dict) -> None:
        if event.get("event_type") != "pointer_down":
            return
        button = event.get("button")
        if button != 1:
            return
        x = event.get("x")
        y = event.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return
        click = PointerClick(x=float(x), y=float(y), button=1)
        self._clicks.append(click)
        if self._on_click_queued is not None:
            self._on_click_queued()
        if self._debug:
            logger.debug("input_click_accepted x=%.1f y=%.1f button=%d", click.x, click.y, click.button)

    @staticmethod
    def _on_any_event(event: dict) -> None:
        event_type = event.get("event_type")
        if event_type not in {"pointer_down", "pointer_up", "pointer_move", "double_click"}:
            return
        logger.debug(
            "input_event type=%s button=%s buttons=%s x=%s y=%s",
            event_type,
            event.get("button"),
            event.get("buttons"),
            event.get("x"),
            event.get("y"),
        )

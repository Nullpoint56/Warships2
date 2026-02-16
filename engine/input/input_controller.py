"""Mouse input mapping to placement and firing actions."""

from __future__ import annotations

import logging
import os
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class PointerClick:
    """Captured pointer click event."""

    x: float
    y: float
    button: int


@dataclass(frozen=True, slots=True)
class PointerEvent:
    """Raw pointer event in canvas coordinates."""

    event_type: str
    x: float
    y: float
    button: int


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """Raw key/char event."""

    event_type: str
    value: str


@dataclass(frozen=True, slots=True)
class WheelEvent:
    """Mouse wheel event in canvas coordinates."""

    x: float
    y: float
    dy: float


logger = logging.getLogger(__name__)


class InputController:
    """Collect pointer events from canvas for polling by app loop."""

    def __init__(self, on_click_queued: Callable[[], None] | None = None) -> None:
        self._clicks: deque[PointerClick] = deque()
        self._pointer_events: deque[PointerEvent] = deque()
        self._key_events: deque[KeyEvent] = deque()
        self._wheel_events: deque[WheelEvent] = deque()
        self._debug = os.getenv("WARSHIPS_DEBUG_INPUT", "0") == "1"
        self._on_click_queued = on_click_queued

    def bind(self, canvas: Any) -> None:
        """Attach pointer listeners to a wgpu canvas."""
        if not hasattr(canvas, "add_event_handler"):
            raise RuntimeError("Canvas does not support event handlers.")
        canvas.add_event_handler(self._on_pointer_down, "pointer_down")
        canvas.add_event_handler(self._on_pointer_move, "pointer_move")
        canvas.add_event_handler(self._on_pointer_up, "pointer_up")
        canvas.add_event_handler(self._on_key_down, "key_down")
        canvas.add_event_handler(self._on_char, "char")
        canvas.add_event_handler(self._on_wheel, "wheel")
        if self._debug:
            canvas.add_event_handler(self._on_any_event, "*")

    def drain_clicks(self) -> list[PointerClick]:
        """Return and clear all queued clicks."""
        items = list(self._clicks)
        self._clicks.clear()
        return items

    def drain_pointer_events(self) -> list[PointerEvent]:
        """Return and clear queued pointer events."""
        items = list(self._pointer_events)
        self._pointer_events.clear()
        return items

    def drain_key_events(self) -> list[KeyEvent]:
        """Return and clear key/char events."""
        items = list(self._key_events)
        self._key_events.clear()
        return items

    def drain_wheel_events(self) -> list[WheelEvent]:
        """Return and clear wheel events."""
        items = list(self._wheel_events)
        self._wheel_events.clear()
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
        self._pointer_events.append(PointerEvent("pointer_down", float(x), float(y), int(button)))
        click = PointerClick(x=float(x), y=float(y), button=1)
        self._clicks.append(click)
        if self._on_click_queued is not None:
            self._on_click_queued()
        if self._debug:
            logger.debug(
                "input_click_accepted x=%.1f y=%.1f button=%d", click.x, click.y, click.button
            )

    def _on_pointer_move(self, event: dict) -> None:
        if event.get("event_type") != "pointer_move":
            return
        x = event.get("x")
        y = event.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return
        button = event.get("button")
        self._pointer_events.append(
            PointerEvent("pointer_move", float(x), float(y), int(button or 0))
        )
        if self._on_click_queued is not None:
            self._on_click_queued()

    def _on_pointer_up(self, event: dict) -> None:
        if event.get("event_type") != "pointer_up":
            return
        x = event.get("x")
        y = event.get("y")
        button = event.get("button")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return
        if not isinstance(button, int):
            button = 0
        self._pointer_events.append(PointerEvent("pointer_up", float(x), float(y), button))
        if self._on_click_queued is not None:
            self._on_click_queued()

    def _on_key_down(self, event: dict) -> None:
        if event.get("event_type") != "key_down":
            return
        key = event.get("key")
        if isinstance(key, str):
            self._key_events.append(KeyEvent("key_down", key))
            if self._on_click_queued is not None:
                self._on_click_queued()

    def _on_char(self, event: dict) -> None:
        if event.get("event_type") != "char":
            return
        char = event.get("data")
        if isinstance(char, str):
            self._key_events.append(KeyEvent("char", char))
            if self._on_click_queued is not None:
                self._on_click_queued()

    def _on_wheel(self, event: dict) -> None:
        if event.get("event_type") != "wheel":
            return
        x = event.get("x")
        y = event.get("y")
        dy = event.get("dy")
        if (
            not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not isinstance(dy, (int, float))
        ):
            return
        self._wheel_events.append(WheelEvent(float(x), float(y), float(dy)))
        if self._on_click_queued is not None:
            self._on_click_queued()

    @staticmethod
    def _on_any_event(event: dict) -> None:
        event_type = event.get("event_type")
        if event_type not in {
            "pointer_down",
            "pointer_up",
            "pointer_move",
            "double_click",
            "wheel",
        }:
            return
        logger.debug(
            "input_event type=%s button=%s buttons=%s x=%s y=%s dy=%s",
            event_type,
            event.get("button"),
            event.get("buttons"),
            event.get("x"),
            event.get("y"),
            event.get("dy"),
        )

"""Mouse input mapping to placement and firing actions."""

from __future__ import annotations

import logging
import os
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import ActionSnapshot, InputSnapshot, KeyboardSnapshot, MouseSnapshot


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
        self._pointer_events: deque[PointerEvent] = deque()
        self._key_events: deque[KeyEvent] = deque()
        self._wheel_events: deque[WheelEvent] = deque()
        self._pressed_keys: set[str] = set()
        self._pressed_buttons: set[int] = set()
        self._pointer_x = 0.0
        self._pointer_y = 0.0
        self._prev_pointer_x = 0.0
        self._prev_pointer_y = 0.0
        self._key_action_bindings: dict[str, str] = {}
        self._pointer_action_bindings: dict[int, str] = {}
        self._char_action_bindings: dict[str, str] = {}
        self._active_actions: set[str] = set()
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
        canvas.add_event_handler(self._on_key_up, "key_up")
        canvas.add_event_handler(self._on_char, "char")
        canvas.add_event_handler(self._on_wheel, "wheel")
        if self._debug:
            canvas.add_event_handler(self._on_any_event, "*")

    def consume_window_input_events(
        self,
        events: tuple[PointerEvent | KeyEvent | WheelEvent, ...],
    ) -> None:
        """Ingest normalized raw input events produced by window layer polling."""
        for raw in events:
            if isinstance(raw, PointerEvent):
                self._pointer_events.append(raw)
                self._pointer_x = float(raw.x)
                self._pointer_y = float(raw.y)
                if raw.event_type == "pointer_down" and int(raw.button) == 1:
                    click = PointerClick(x=float(raw.x), y=float(raw.y), button=1)
                    self._clicks.append(click)
                if self._on_click_queued is not None:
                    self._on_click_queued()
                continue
            if isinstance(raw, KeyEvent):
                self._key_events.append(raw)
                if self._on_click_queued is not None:
                    self._on_click_queued()
                continue
            if isinstance(raw, WheelEvent):
                self._wheel_events.append(raw)
                if self._on_click_queued is not None:
                    self._on_click_queued()

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

    def bind_action_key_down(self, key_name: str, action_name: str) -> None:
        """Bind normalized key-down to logical action."""
        normalized = key_name.strip().lower()
        if not normalized:
            raise ValueError("key_name must not be empty")
        self._key_action_bindings[normalized] = action_name

    def bind_action_pointer_down(self, button: int, action_name: str) -> None:
        """Bind pointer-down button to logical action."""
        if button < 0:
            raise ValueError("button must be >= 0")
        self._pointer_action_bindings[button] = action_name

    def bind_action_char(self, char_value: str, action_name: str) -> None:
        """Bind char input to logical action."""
        if not char_value:
            raise ValueError("char_value must not be empty")
        self._char_action_bindings[char_value] = action_name

    def build_input_snapshot(self, *, frame_index: int) -> InputSnapshot:
        """Build one immutable per-frame snapshot and consume queued raw events."""
        pointer_events = tuple(self.drain_pointer_events())
        key_events = tuple(self.drain_key_events())
        wheel_events = tuple(self.drain_wheel_events())

        just_pressed_buttons: set[int] = set()
        just_released_buttons: set[int] = set()
        wheel_delta = 0.0
        for pointer_event in pointer_events:
            self._pointer_x = float(pointer_event.x)
            self._pointer_y = float(pointer_event.y)
            button = int(pointer_event.button)
            if pointer_event.event_type == "pointer_down" and button > 0:
                just_pressed_buttons.add(button)
                self._pressed_buttons.add(button)
            elif pointer_event.event_type == "pointer_up" and button > 0:
                just_released_buttons.add(button)
                self._pressed_buttons.discard(button)
        for wheel_event in wheel_events:
            wheel_delta += float(wheel_event.dy)

        just_pressed_keys: set[str] = set()
        just_released_keys: set[str] = set()
        text_input: list[str] = []
        just_started_actions: set[str] = set()
        just_ended_actions: set[str] = set()
        for key_event in key_events:
            value = str(key_event.value)
            if key_event.event_type == "key_down":
                norm = value.strip().lower()
                if norm:
                    just_pressed_keys.add(norm)
                    self._pressed_keys.add(norm)
                    action = self._key_action_bindings.get(norm)
                    if action is not None and action not in self._active_actions:
                        self._active_actions.add(action)
                        just_started_actions.add(action)
            elif key_event.event_type == "key_up":
                norm = value.strip().lower()
                if norm:
                    just_released_keys.add(norm)
                    self._pressed_keys.discard(norm)
                    action = self._key_action_bindings.get(norm)
                    if action is not None and action in self._active_actions:
                        self._active_actions.discard(action)
                        just_ended_actions.add(action)
            elif key_event.event_type == "char":
                text_input.append(value)
                action = self._char_action_bindings.get(value)
                if action is not None:
                    just_started_actions.add(action)

        delta_x = self._pointer_x - self._prev_pointer_x
        delta_y = self._pointer_y - self._prev_pointer_y
        self._prev_pointer_x = self._pointer_x
        self._prev_pointer_y = self._pointer_y

        for pointer_event in pointer_events:
            button = int(pointer_event.button)
            if pointer_event.event_type == "pointer_down":
                action = self._pointer_action_bindings.get(button)
                if action is not None and action not in self._active_actions:
                    self._active_actions.add(action)
                    just_started_actions.add(action)
            elif pointer_event.event_type == "pointer_up":
                action = self._pointer_action_bindings.get(button)
                if action is not None and action in self._active_actions:
                    self._active_actions.discard(action)
                    just_ended_actions.add(action)

        keyboard = KeyboardSnapshot(
            pressed_keys=frozenset(self._pressed_keys),
            just_pressed_keys=frozenset(just_pressed_keys),
            just_released_keys=frozenset(just_released_keys),
            text_input=tuple(text_input),
        )
        mouse = MouseSnapshot(
            x=self._pointer_x,
            y=self._pointer_y,
            delta_x=delta_x,
            delta_y=delta_y,
            wheel_delta=wheel_delta,
            pressed_buttons=frozenset(self._pressed_buttons),
            just_pressed_buttons=frozenset(just_pressed_buttons),
            just_released_buttons=frozenset(just_released_buttons),
        )
        actions = ActionSnapshot(
            active=frozenset(self._active_actions),
            just_started=frozenset(just_started_actions),
            just_ended=frozenset(just_ended_actions),
        )
        return InputSnapshot(
            frame_index=frame_index,
            keyboard=keyboard,
            mouse=mouse,
            actions=actions,
            pointer_events=pointer_events,
            key_events=key_events,
            wheel_events=wheel_events,
        )

    def _on_pointer_down(self, event: dict[str, Any]) -> None:
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

    def _on_pointer_move(self, event: dict[str, Any]) -> None:
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

    def _on_pointer_up(self, event: dict[str, Any]) -> None:
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

    def _on_key_down(self, event: dict[str, Any]) -> None:
        if event.get("event_type") != "key_down":
            return
        key = event.get("key")
        if isinstance(key, str):
            self._key_events.append(KeyEvent("key_down", key))
            if self._on_click_queued is not None:
                self._on_click_queued()

    def _on_key_up(self, event: dict[str, Any]) -> None:
        if event.get("event_type") != "key_up":
            return
        key = event.get("key")
        if isinstance(key, str):
            self._key_events.append(KeyEvent("key_up", key))
            if self._on_click_queued is not None:
                self._on_click_queued()

    def _on_char(self, event: dict[str, Any]) -> None:
        if event.get("event_type") != "char":
            return
        char = event.get("data")
        if isinstance(char, str):
            self._key_events.append(KeyEvent("char", char))
            if self._on_click_queued is not None:
                self._on_click_queued()

    def _on_wheel(self, event: dict[str, Any]) -> None:
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
    def _on_any_event(event: dict[str, Any]) -> None:
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

"""Main application loop orchestration."""

from __future__ import annotations

import os
import random
from pathlib import Path
import time

from warships.app.controller import GameController
from warships.app.events import ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService
from warships.ui.board_view import BoardLayout
from warships.ui.game_view import GameView
from warships.ui.input_controller import InputController, PointerClick, PointerEvent, KeyEvent
from warships.ui.scene import SceneRenderer


class AppLoop:
    """Coordinates input routing and rendering around the controller."""

    def __init__(self) -> None:
        self._layout = BoardLayout()
        self._renderer = SceneRenderer()
        self._view = GameView(self._renderer, self._layout)
        self._input = InputController(on_click_queued=self._renderer.invalidate)
        self._input.bind(self._renderer.canvas)

        preset_service = PresetService(PresetRepository(Path("data/presets")))
        self._debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._controller = GameController(
            preset_service=preset_service,
            rng=random.Random(),
            debug_ui=self._debug_ui,
        )

        self._last_click_ts = 0.0
        self._last_click_pos: tuple[float, float] | None = None
        self._last_debug_buttons: list[str] = []

    def run(self) -> None:
        """Start the application loop."""
        self._renderer.run(self._draw_frame)

    def _draw_frame(self) -> None:
        self._process_inputs()
        ui = self._controller.ui_state()
        if ui.is_closing:
            self._renderer.close()
            return
        self._last_debug_buttons = self._view.render(
            ui=ui,
            debug_ui=self._debug_ui,
            debug_labels_state=self._last_debug_buttons,
        )

    def _process_inputs(self) -> None:
        for key_event in self._input.drain_key_events():
            self._handle_key_event(key_event)
        for pointer_event in self._input.drain_pointer_events():
            self._handle_pointer_event(pointer_event)
        clicks = self._input.drain_clicks()
        if not clicks:
            return
        self._handle_click(clicks[0])

    def _handle_click(self, click: PointerClick) -> None:
        if click.button != 1:
            return
        norm_x, norm_y = self._renderer.to_design_space(click.x, click.y)
        now = time.monotonic()
        if now - self._last_click_ts < 0.20 and self._last_click_pos == (norm_x, norm_y):
            return
        self._last_click_ts = now
        self._last_click_pos = (norm_x, norm_y)

        ui = self._controller.ui_state()
        for button in ui.buttons:
            if button.enabled and button.contains(norm_x, norm_y):
                changed = self._controller.handle_button(ButtonPressed(button.id))
                if changed:
                    self._renderer.invalidate()
                return

        # Placement editor is drag/drop and handled via pointer down/move/up.

    def _handle_pointer_event(self, event: PointerEvent) -> None:
        x, y = self._renderer.to_design_space(event.x, event.y)
        changed = False
        if event.event_type == "pointer_down":
            changed = self._controller.handle_pointer_down(x, y, event.button)
        elif event.event_type == "pointer_move":
            changed = self._controller.handle_pointer_move(PointerMoved(x=x, y=y))
        elif event.event_type == "pointer_up":
            changed = self._controller.handle_pointer_release(PointerReleased(x=x, y=y, button=event.button))
        if changed:
            self._renderer.invalidate()

    def _handle_key_event(self, event: KeyEvent) -> None:
        changed = False
        if event.event_type == "key_down":
            changed = self._controller.handle_key_pressed(KeyPressed(key=event.value))
        elif event.event_type == "char":
            changed = self._controller.handle_char_typed(CharTyped(char=event.value))
        if changed:
            self._renderer.invalidate()

"""Main application loop orchestration."""

from __future__ import annotations

import os
import random
from pathlib import Path
import time

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed
from warships.app.state_machine import AppState
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService
from warships.ui.board_view import BoardLayout
from warships.ui.game_view import GameView
from warships.ui.input_controller import InputController, PointerClick
from warships.ui.scene import SceneRenderer


class AppLoop:
    """Coordinates input routing and rendering around the controller."""

    def __init__(self) -> None:
        self._layout = BoardLayout()
        self._renderer = SceneRenderer()
        self._view = GameView(self._renderer, self._layout)
        self._input = InputController(on_click_queued=self._renderer.invalidate)
        self._input.bind(self._renderer.canvas)
        if hasattr(self._renderer.canvas, "add_event_handler"):
            self._renderer.canvas.add_event_handler(self._on_resize, "resize")

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
        clicks = self._input.drain_clicks()
        if not clicks:
            return
        self._handle_click(clicks[0])

    def _handle_click(self, click: PointerClick) -> None:
        if click.button != 1:
            return
        norm_x, norm_y = self._to_design_space(click.x, click.y)
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

        if ui.state is AppState.PLACEMENT_EDIT:
            coord = self._layout.screen_to_cell(is_ai=False, px=norm_x, py=norm_y)
            if coord is None:
                return
            changed = self._controller.handle_board_click(BoardCellPressed(is_ai_board=False, coord=coord))
            if changed:
                self._renderer.invalidate()
            return

        if ui.state is AppState.BATTLE:
            coord = self._layout.screen_to_cell(is_ai=True, px=norm_x, py=norm_y)
            if coord is None:
                return
            changed = self._controller.handle_board_click(BoardCellPressed(is_ai_board=True, coord=coord))
            if changed:
                self._renderer.invalidate()

    def _to_design_space(self, x: float, y: float) -> tuple[float, float]:
        """Map click coordinates from current logical canvas size to design space."""
        if not hasattr(self._renderer.canvas, "get_logical_size"):
            return x, y
        size = self._renderer.canvas.get_logical_size()
        if not isinstance(size, tuple) or len(size) != 2:
            return x, y
        current_w, current_h = float(size[0]), float(size[1])
        if current_w <= 1.0 or current_h <= 1.0:
            return x, y
        return (
            x * (self._renderer.width / current_w),
            y * (self._renderer.height / current_h),
        )

    def _on_resize(self, _event: dict) -> None:
        """Ensure a redraw when canvas size changes."""
        self._renderer.invalidate()

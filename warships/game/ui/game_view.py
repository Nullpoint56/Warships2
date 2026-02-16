"""Retained-mode game rendering for Warships."""

from __future__ import annotations

import logging

from engine.api.render import RenderAPI as Render2D
from engine.ui_runtime.grid_layout import GridLayout
from engine.ui_runtime.widgets import Button
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.ui.framework.widgets import (
    build_modal_text_input_widget,
    render_modal_text_input_widget,
)
from warships.game.ui.overlays import button_label
from warships.game.ui.views import (
    draw_ai_board,
    draw_new_game_setup,
    draw_placement_panel,
    draw_player_board,
    draw_preset_manage,
    draw_status_bar,
    is_new_game_custom_button,
)

logger = logging.getLogger(__name__)


class GameView:
    """Draws game state using retained keyed scene nodes."""

    def __init__(self, renderer: Render2D, layout: GridLayout) -> None:
        self._renderer = renderer
        self._layout = layout

    def render(
        self,
        ui: AppUIState,
        debug_ui: bool,
        debug_labels_state: list[str],
    ) -> list[str]:
        """Draw current app state and return latest button labels for debug."""
        self._renderer.begin_frame()
        self._renderer.fill_window("bg:window", "#0b132b", z=-100.0)

        labels = self._draw_buttons(ui.buttons)
        if ui.state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            draw_player_board(
                renderer=self._renderer,
                layout=self._layout,
                placements=ui.placements,
                session=ui.session,
                held_ship_type=ui.held_ship_type,
                held_orientation=ui.held_ship_orientation,
                held_grab_index=ui.held_grab_index,
                hover_cell=ui.hover_cell,
                hover_x=ui.hover_x,
                hover_y=ui.hover_y,
            )
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            draw_ai_board(renderer=self._renderer, layout=self._layout, session=ui.session)
        if ui.state is AppState.PLACEMENT_EDIT:
            draw_placement_panel(self._renderer, ui.placements, ui.ship_order)
        if ui.state is AppState.PRESET_MANAGE:
            draw_preset_manage(self._renderer, ui)
        if ui.state is AppState.NEW_GAME_SETUP:
            draw_new_game_setup(self._renderer, ui)

        prompt_widget = build_modal_text_input_widget(ui)
        if prompt_widget is not None:
            render_modal_text_input_widget(self._renderer, prompt_widget)

        draw_status_bar(
            renderer=self._renderer,
            state=ui.state,
            status=ui.status,
            placement_orientation=ui.placement_orientation,
            placements=ui.placements,
            ship_order=ui.ship_order,
        )
        self._renderer.set_title(f"Warships V1 | {ui.status}")

        if debug_ui and labels != debug_labels_state:
            logger.debug("ui_button_labels labels=%s", labels)
        self._renderer.end_frame()
        return labels

    def _draw_buttons(self, buttons: list[Button]) -> list[str]:
        labels: list[str] = []
        for button in buttons:
            if is_new_game_custom_button(button.id):
                continue
            color = "#1f6feb" if button.enabled else "#384151"
            z = 10.4 if button.id.startswith("prompt_") else 1.0
            self._renderer.add_rect(
                f"button:bg:{button.id}",
                button.x,
                button.y,
                button.w,
                button.h,
                color,
                z=z,
            )
            label = button_label(button.id)
            labels.append(label)
            self._renderer.add_text(
                key=f"button:text:{button.id}",
                text=label,
                x=button.x + button.w / 2.0,
                y=button.y + button.h / 2.0,
                font_size=17.0,
                color="#e5e7eb",
                anchor="middle-center",
                z=10.5 if button.id.startswith("prompt_") else 3.0,
            )
        return labels

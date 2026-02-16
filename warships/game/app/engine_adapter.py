"""Adapter between GameController and engine app port contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from engine.api.app_port import (
    ButtonView,
    EngineAppPort,
    InteractionPlanView,
    ModalWidgetView,
    RectView,
)
from warships.game.app.controller import GameController
from warships.game.app.events import (
    BoardCellPressed,
    ButtonPressed,
    CharTyped,
    KeyPressed,
    PointerMoved,
    PointerReleased,
)
from warships.game.app.shortcut_policy import shortcut_buttons_for_state
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.core.models import Coord
from warships.game.ui.framework.widgets import build_modal_text_input_widget
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL


@dataclass(slots=True)
class _EngineInteractionPlan:
    """Engine runtime-compatible interaction plan."""

    buttons: tuple[ButtonView, ...]
    shortcut_buttons: dict[str, str]
    grid_click_target: str | None
    wheel_scroll_regions: tuple[RectView, ...]


class WarshipsAppAdapter(EngineAppPort):
    """EngineAppPort implementation backed by GameController."""

    def __init__(self, controller: GameController) -> None:
        self._controller = controller

    def ui_state(self) -> AppUIState:  # noqa: D401
        return self._controller.ui_state()

    def modal_widget(self) -> ModalWidgetView | None:
        return cast(
            ModalWidgetView | None, build_modal_text_input_widget(self._controller.ui_state())
        )

    def interaction_plan(self) -> InteractionPlanView:
        ui = self._controller.ui_state()
        state = ui.state
        wheel_scroll_regions: list[RectView] = []
        if state is AppState.NEW_GAME_SETUP:
            wheel_scroll_regions.append(NEW_GAME_SETUP.preset_list_rect())
        if state is AppState.PRESET_MANAGE:
            wheel_scroll_regions.append(PRESET_PANEL.panel_rect())
        return _EngineInteractionPlan(
            buttons=tuple(cast(ButtonView, button) for button in ui.buttons),
            shortcut_buttons=shortcut_buttons_for_state(state),
            grid_click_target="secondary" if state is AppState.BATTLE else None,
            wheel_scroll_regions=tuple(wheel_scroll_regions),
        )

    def on_button(self, button_id: str) -> bool:
        return self._controller.handle_button(ButtonPressed(button_id))

    def on_grid_click(self, grid_target: str, row: int, col: int) -> bool:
        is_ai_board = grid_target.strip().lower() in {"secondary", "opponent", "enemy", "ai"}
        return self._controller.handle_board_click(
            BoardCellPressed(is_ai_board, Coord(row=row, col=col))
        )

    def on_pointer_move(self, x: float, y: float) -> bool:
        return self._controller.handle_pointer_move(PointerMoved(x=x, y=y))

    def on_pointer_release(self, x: float, y: float, button: int) -> bool:
        return self._controller.handle_pointer_release(PointerReleased(x=x, y=y, button=button))

    def on_pointer_down(self, x: float, y: float, button: int) -> bool:
        return self._controller.handle_pointer_down(x, y, button)

    def on_key(self, key: str) -> bool:
        return self._controller.handle_key_pressed(KeyPressed(key))

    def on_char(self, value: str) -> bool:
        return self._controller.handle_char_typed(CharTyped(value))

    def on_wheel(self, x: float, y: float, dy: float) -> bool:
        return self._controller.handle_wheel(x, y, dy)

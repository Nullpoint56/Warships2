"""Adapter between GameController and engine app port contract."""

from __future__ import annotations

from dataclasses import dataclass

from warships.game.app.controller import GameController
from warships.game.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.game.app.state_machine import AppState
from warships.game.app.shortcut_policy import shortcut_buttons_for_state
from warships.game.core.models import Coord
from engine.api.app_port import ButtonView, EngineAppPort, InteractionPlanView, ModalWidgetView, RectView
from warships.game.ui.framework.widgets import build_modal_text_input_widget
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL


@dataclass(frozen=True, slots=True)
class _EngineInteractionPlan:
    """Engine runtime-compatible interaction plan."""

    buttons: tuple[ButtonView, ...]
    shortcut_buttons: dict[str, str]
    allows_ai_board_click: bool
    wheel_scroll_in_new_game_list: bool
    wheel_scroll_in_preset_manage_panel: bool
    new_game_list_rect: RectView | None
    preset_manage_rect: RectView | None


class WarshipsAppAdapter(EngineAppPort):
    """EngineAppPort implementation backed by GameController."""

    def __init__(self, controller: GameController) -> None:
        self._controller = controller

    def ui_state(self):  # noqa: D401
        return self._controller.ui_state()

    def modal_widget(self) -> ModalWidgetView | None:
        return build_modal_text_input_widget(self._controller.ui_state())

    def interaction_plan(self) -> InteractionPlanView:
        ui = self._controller.ui_state()
        state = ui.state
        wheel_new_game = state is AppState.NEW_GAME_SETUP
        wheel_preset_manage = state is AppState.PRESET_MANAGE
        return _EngineInteractionPlan(
            buttons=tuple(ui.buttons),
            shortcut_buttons=shortcut_buttons_for_state(state),
            allows_ai_board_click=state is AppState.BATTLE,
            wheel_scroll_in_new_game_list=wheel_new_game,
            wheel_scroll_in_preset_manage_panel=wheel_preset_manage,
            new_game_list_rect=NEW_GAME_SETUP.preset_list_rect() if wheel_new_game else None,
            preset_manage_rect=PRESET_PANEL.panel_rect() if wheel_preset_manage else None,
        )

    def on_button(self, button_id: str) -> bool:
        return self._controller.handle_button(ButtonPressed(button_id))

    def on_board_click(self, is_ai_board: bool, row: int, col: int) -> bool:
        return self._controller.handle_board_click(BoardCellPressed(is_ai_board, Coord(row=row, col=col)))

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



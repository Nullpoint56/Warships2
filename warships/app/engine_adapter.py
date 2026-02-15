"""Adapter between GameController and engine app port contract."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.core.models import Coord
from warships.engine.api.app_port import ButtonView, EngineAppPort, InteractionPlanView, ModalWidgetView, RectView
from warships.ui.framework.widgets import build_modal_text_input_widget
from warships.ui.framework.interactions import build_interaction_plan
from warships.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL


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
        plan = build_interaction_plan(self._controller.ui_state())
        return _EngineInteractionPlan(
            buttons=plan.buttons,
            shortcut_buttons=plan.shortcut_buttons,
            allows_ai_board_click=plan.allows_ai_board_click,
            wheel_scroll_in_new_game_list=plan.wheel_scroll_in_new_game_list,
            wheel_scroll_in_preset_manage_panel=plan.wheel_scroll_in_preset_manage_panel,
            new_game_list_rect=NEW_GAME_SETUP.preset_list_rect() if plan.wheel_scroll_in_new_game_list else None,
            preset_manage_rect=PRESET_PANEL.panel_rect() if plan.wheel_scroll_in_preset_manage_panel else None,
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

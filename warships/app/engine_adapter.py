"""Adapter between GameController and engine app port contract."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.core.models import Coord
from warships.engine.api.app_port import EngineAppPort


class WarshipsAppAdapter(EngineAppPort):
    """EngineAppPort implementation backed by GameController."""

    def __init__(self, controller: GameController) -> None:
        self._controller = controller

    def ui_state(self):  # noqa: D401
        return self._controller.ui_state()

    def on_button(self, button_id: str) -> bool:
        return self._controller.handle_button(ButtonPressed(button_id))

    def on_board_click(self, is_ai_board: bool, coord: Coord) -> bool:
        return self._controller.handle_board_click(BoardCellPressed(is_ai_board, coord))

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


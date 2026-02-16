from __future__ import annotations

from types import SimpleNamespace

from warships.game.app.engine_adapter import WarshipsAppAdapter
from warships.game.app.state_machine import AppState


class _StubController:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self.calls: list[tuple[str, tuple]] = []

    def ui_state(self):
        return SimpleNamespace(state=self._state, buttons=[], prompt=None)

    def handle_button(self, event):
        self.calls.append(("button", (event.button_id,)))
        return True

    def handle_board_click(self, event):
        self.calls.append(("board", (event.is_ai_board, event.coord.row, event.coord.col)))
        return True

    def handle_pointer_move(self, event):
        self.calls.append(("move", (event.x, event.y)))
        return True

    def handle_pointer_release(self, event):
        self.calls.append(("up", (event.x, event.y, event.button)))
        return True

    def handle_pointer_down(self, x, y, button):
        self.calls.append(("down", (x, y, button)))
        return True

    def handle_key_pressed(self, event):
        self.calls.append(("key", (event.key,)))
        return True

    def handle_char_typed(self, event):
        self.calls.append(("char", (event.char,)))
        return True

    def handle_wheel(self, x, y, dy):
        self.calls.append(("wheel", (x, y, dy)))
        return True


def test_adapter_interaction_plan_maps_state() -> None:
    battle = WarshipsAppAdapter(_StubController(AppState.BATTLE))
    plan_battle = battle.interaction_plan()
    assert plan_battle.grid_click_target == "secondary"

    manage = WarshipsAppAdapter(_StubController(AppState.PRESET_MANAGE))
    plan_manage = manage.interaction_plan()
    assert plan_manage.grid_click_target is None
    assert len(plan_manage.wheel_scroll_regions) == 1


def test_adapter_on_grid_click_maps_target_to_ai_flag() -> None:
    controller = _StubController(AppState.BATTLE)
    adapter = WarshipsAppAdapter(controller)
    assert adapter.on_grid_click("secondary", 2, 3)
    assert controller.calls[-1] == ("board", (True, 2, 3))
    assert adapter.on_grid_click("primary", 1, 1)
    assert controller.calls[-1] == ("board", (False, 1, 1))


def test_adapter_forwards_input_methods() -> None:
    controller = _StubController(AppState.MAIN_MENU)
    adapter = WarshipsAppAdapter(controller)
    adapter.on_button("new_game")
    adapter.on_pointer_move(1.0, 2.0)
    adapter.on_pointer_release(3.0, 4.0, 1)
    adapter.on_pointer_down(5.0, 6.0, 1)
    adapter.on_key("escape")
    adapter.on_char("x")
    adapter.on_wheel(7.0, 8.0, 1.0)
    assert [name for name, _ in controller.calls] == [
        "button",
        "move",
        "up",
        "down",
        "key",
        "char",
        "wheel",
    ]

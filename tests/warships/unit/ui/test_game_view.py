from __future__ import annotations

from engine.ui_runtime.grid_layout import GridLayout
from tests.warships.unit.ui.helpers import FakeRenderer, make_ui_state
from warships.game.app.state_machine import AppState
from warships.game.ui.game_view import GameView


class _Render(FakeRenderer):
    def __init__(self) -> None:
        super().__init__()
        self.begun = 0
        self.ended = 0
        self.window_fill = 0
        self.titles: list[str] = []

    def begin_frame(self) -> None:
        self.begun += 1

    def end_frame(self) -> None:
        self.ended += 1

    def fill_window(self, *args, **kwargs) -> None:
        _ = (args, kwargs)
        self.window_fill += 1

    def set_title(self, title: str) -> None:
        self.titles.append(title)


def test_game_view_render_main_menu() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.MAIN_MENU)
    labels = view.render(ui, debug_ui=False, debug_labels_state=[])
    assert renderer.begun == 1 and renderer.ended == 1 and renderer.window_fill == 1
    assert labels


def test_game_view_skips_new_game_custom_buttons_in_overlay() -> None:
    renderer = _Render()
    view = GameView(renderer, GridLayout())
    ui = make_ui_state(state=AppState.NEW_GAME_SETUP, new_game_visible_presets=["a"])
    labels = view.render(ui, debug_ui=False, debug_labels_state=[])
    assert renderer.begun == 1 and renderer.ended == 1
    assert isinstance(labels, list)

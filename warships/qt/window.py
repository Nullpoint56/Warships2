"""Main Qt window and page routing."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.events import ButtonPressed
from warships.app.frontend import FrontendWindow
from warships.app.state_machine import AppState
from warships.qt.canvas import GameCanvas
from warships.qt.pages import MainMenuPage, NewGamePage, PresetManagerPage
from warships.qt.prompt_coordinator import PromptCoordinator
from warships.ui.board_view import BoardLayout

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


class MainWindow(QMainWindow):
    def __init__(self, controller: GameController) -> None:
        super().__init__()
        self._controller = controller
        self._layout = BoardLayout()
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._main = MainMenuPage(self._click_button)
        self._new = NewGamePage(self._click_button, self._scroll_new_game_presets)
        self._presets = PresetManagerPage(self._click_button)
        self._canvas = GameCanvas(controller, self._layout, self._click_button)
        self._stack.addWidget(self._main)
        self._stack.addWidget(self._new)
        self._stack.addWidget(self._presets)
        self._stack.addWidget(self._canvas)
        self._prompt_coordinator = PromptCoordinator(self, self._controller)
        self.setWindowTitle("Warships V1")

    def click_button(self, button_id: str) -> None:
        self._click_button(button_id)

    def sync_ui(self) -> None:
        self._sync_ui()

    def _click_button(self, button_id: str) -> None:
        if self._controller.handle_button(ButtonPressed(button_id)):
            self._sync_ui()

    def _scroll_new_game_presets(self, dy: float) -> bool:
        if self._controller.scroll_new_game_presets(dy):
            self._sync_ui()
            return True
        return False

    def _sync_ui(self) -> None:
        ui = self._prompt_coordinator.sync_prompts(self._controller.ui_state())
        if ui.state is AppState.MAIN_MENU:
            self._main.sync(ui)
            self._stack.setCurrentWidget(self._main)
        elif ui.state is AppState.NEW_GAME_SETUP:
            self._new.sync(ui)
            self._stack.setCurrentWidget(self._new)
        elif ui.state is AppState.PRESET_MANAGE:
            self._presets.sync(ui)
            self._stack.setCurrentWidget(self._presets)
        else:
            self._stack.setCurrentWidget(self._canvas)
            self._canvas.update()
            self._canvas.setFocus()
        if ui.is_closing:
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        ui = self._controller.ui_state()
        if event.key() == Qt.Key.Key_Escape:
            if ui.state is AppState.NEW_GAME_SETUP:
                self._click_button("back_main")
                return
            if ui.state is AppState.PRESET_MANAGE:
                self._click_button("back_main")
                return
            if ui.state is AppState.PLACEMENT_EDIT:
                self._click_button("back_to_presets")
                return
            if ui.state is AppState.BATTLE:
                self._click_button("back_main")
                return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            if ui.state is AppState.MAIN_MENU:
                self._click_button("new_game")
                return
            if ui.state is AppState.NEW_GAME_SETUP:
                self._click_button("start_game")
                return
            if ui.state is AppState.PRESET_MANAGE:
                self._click_button("create_preset")
                return
            if ui.state is AppState.PLACEMENT_EDIT:
                self._click_button("save_preset")
                return
            if ui.state is AppState.RESULT:
                self._click_button("play_again")
                return
        super().keyPressEvent(event)


class QtFrontendWindow(FrontendWindow):
    """Frontend adapter over the Qt main window."""

    def __init__(self, window: MainWindow) -> None:
        self._window = window

    def show_fullscreen(self) -> None:
        self._window.showFullScreen()

    def show_maximized(self) -> None:
        self._window.showMaximized()

    def show_windowed(self, width: int, height: int) -> None:
        self._window.resize(width, height)
        self._window.show()

    def sync_ui(self) -> None:
        self._window.sync_ui()

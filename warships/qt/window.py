"""Main Qt window and page routing."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.events import ButtonPressed
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.qt.canvas import GameCanvas
from warships.qt.pages import MainMenuPage, NewGamePage, PresetManagerPage
from warships.ui.board_view import BoardLayout

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QInputDialog, QMainWindow, QMessageBox, QStackedWidget
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
        self._new = NewGamePage(self._click_button)
        self._presets = PresetManagerPage(self._click_button)
        self._canvas = GameCanvas(controller, self._layout, self._click_button)
        self._stack.addWidget(self._main)
        self._stack.addWidget(self._new)
        self._stack.addWidget(self._presets)
        self._stack.addWidget(self._canvas)
        self.setWindowTitle("Warships V1")

    def click_button(self, button_id: str) -> None:
        self._click_button(button_id)

    def sync_ui(self) -> None:
        self._sync_ui()

    def _click_button(self, button_id: str) -> None:
        if self._controller.handle_button(ButtonPressed(button_id)):
            self._sync_ui()

    def _sync_prompt(self, ui: AppUIState) -> None:
        if ui.prompt is None:
            return
        if ui.prompt.confirm_button_id == "prompt_confirm_overwrite":
            answer = QMessageBox.question(
                self,
                ui.prompt.title,
                f"Overwrite preset '{ui.prompt.value}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._controller.handle_button(ButtonPressed(ui.prompt.confirm_button_id))
            else:
                self._controller.handle_button(ButtonPressed(ui.prompt.cancel_button_id))
            return
        text, ok = QInputDialog.getText(self, ui.prompt.title, ui.prompt.title, text=ui.prompt.value)
        if not ok:
            self._controller.cancel_prompt()
            return
        self._controller.submit_prompt_text(text)

    def _sync_ui(self) -> None:
        ui = self._controller.ui_state()
        while ui.prompt is not None:
            before = (ui.prompt.title, ui.prompt.value, ui.prompt.confirm_button_id)
            self._sync_prompt(ui)
            ui = self._controller.ui_state()
            after_prompt = ui.prompt
            if after_prompt is not None:
                after = (after_prompt.title, after_prompt.value, after_prompt.confirm_button_id)
                if after == before:
                    break
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

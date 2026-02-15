"""Prompt orchestration for Qt dialogs."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.events import ButtonPressed
from warships.app.ui_state import AppUIState

try:
    from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


class PromptCoordinator:
    """Runs controller prompt flows using native Qt dialogs."""

    def __init__(self, owner: QWidget, controller: GameController) -> None:
        self._owner = owner
        self._controller = controller

    def sync_prompts(self, ui: AppUIState) -> AppUIState:
        """Drain prompt interactions and return latest controller UI state."""
        current = ui
        while current.prompt is not None:
            before = (current.prompt.title, current.prompt.value, current.prompt.confirm_button_id)
            self._show_prompt(current)
            current = self._controller.ui_state()
            after_prompt = current.prompt
            if after_prompt is not None:
                after = (after_prompt.title, after_prompt.value, after_prompt.confirm_button_id)
                if after == before:
                    break
        return current

    def _show_prompt(self, ui: AppUIState) -> None:
        prompt = ui.prompt
        if prompt is None:
            return
        if prompt.confirm_button_id == "prompt_confirm_overwrite":
            answer = QMessageBox.question(
                self._owner,
                prompt.title,
                f"Overwrite preset '{prompt.value}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._controller.handle_button(ButtonPressed(prompt.confirm_button_id))
            else:
                self._controller.handle_button(ButtonPressed(prompt.cancel_button_id))
            return
        text, ok = QInputDialog.getText(self._owner, prompt.title, prompt.title, text=prompt.value)
        if not ok:
            self._controller.cancel_prompt()
            return
        self._controller.submit_prompt_text(text)


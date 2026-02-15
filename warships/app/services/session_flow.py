"""App/session navigation transitions for controller orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from warships.app.state_machine import AppState


@dataclass(frozen=True, slots=True)
class AppTransition:
    """State transition intent emitted by session/navigation flow."""

    state: AppState
    status: str
    refresh_preset_rows: bool = False
    refresh_buttons: bool = True
    announce_state: bool = True
    clear_session: bool = False
    reset_editor: bool = False
    clear_editing_preset_name: bool = False
    enter_new_game_setup: bool = False


class SessionFlowService:
    """Pure transition helpers for app-level screen/session navigation."""

    @staticmethod
    def to_manage_presets() -> AppTransition:
        return AppTransition(
            state=AppState.PRESET_MANAGE,
            status="Manage presets.",
            refresh_preset_rows=True,
        )

    @staticmethod
    def to_new_game_setup() -> AppTransition:
        return AppTransition(
            state=AppState.NEW_GAME_SETUP,
            status="Configure game: difficulty and fleet selection.",
            enter_new_game_setup=True,
        )

    @staticmethod
    def to_create_preset() -> AppTransition:
        return AppTransition(
            state=AppState.PLACEMENT_EDIT,
            status="Drag a ship from panel, drop onto board. Press R while holding to rotate.",
            reset_editor=True,
            clear_editing_preset_name=True,
        )

    @staticmethod
    def to_main_menu() -> AppTransition:
        return AppTransition(
            state=AppState.MAIN_MENU,
            status="Choose New Game, Manage Presets, or Quit.",
            clear_session=True,
        )

    @staticmethod
    def to_back_to_presets() -> AppTransition:
        return AppTransition(
            state=AppState.PRESET_MANAGE,
            status="Manage presets.",
            refresh_preset_rows=True,
        )


"""App/session navigation transitions for controller orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.flow import FlowTransition, create_flow_program
from warships.game.app.state_machine import AppState


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

    _PROGRAM = create_flow_program(
        (
            FlowTransition(
                trigger="to_manage_presets",
                source=None,
                target=AppState.PRESET_MANAGE,
            ),
            FlowTransition(
                trigger="to_new_game_setup",
                source=None,
                target=AppState.NEW_GAME_SETUP,
            ),
            FlowTransition(
                trigger="to_create_preset",
                source=None,
                target=AppState.PLACEMENT_EDIT,
            ),
            FlowTransition(
                trigger="to_main_menu",
                source=None,
                target=AppState.MAIN_MENU,
            ),
            FlowTransition(
                trigger="to_back_to_presets",
                source=None,
                target=AppState.PRESET_MANAGE,
            ),
        )
    )

    @staticmethod
    def to_manage_presets(current_state: AppState) -> AppTransition | None:
        return SessionFlowService.resolve(current_state, "to_manage_presets")

    @staticmethod
    def to_new_game_setup(current_state: AppState) -> AppTransition | None:
        return SessionFlowService.resolve(current_state, "to_new_game_setup")

    @staticmethod
    def to_create_preset(current_state: AppState) -> AppTransition | None:
        return SessionFlowService.resolve(current_state, "to_create_preset")

    @staticmethod
    def to_main_menu(current_state: AppState) -> AppTransition | None:
        return SessionFlowService.resolve(current_state, "to_main_menu")

    @staticmethod
    def to_back_to_presets(current_state: AppState) -> AppTransition | None:
        return SessionFlowService.resolve(current_state, "to_back_to_presets")

    @staticmethod
    def resolve(current_state: AppState, trigger: str) -> AppTransition | None:
        """Resolve navigation trigger using reusable engine flow program."""
        next_state = SessionFlowService._PROGRAM.resolve(current_state, trigger)
        if next_state is None:
            return None
        if trigger == "to_manage_presets" and next_state is AppState.PRESET_MANAGE:
            return AppTransition(
                state=AppState.PRESET_MANAGE,
                status="Manage presets.",
                refresh_preset_rows=True,
            )
        if trigger == "to_new_game_setup" and next_state is AppState.NEW_GAME_SETUP:
            return AppTransition(
                state=AppState.NEW_GAME_SETUP,
                status="Configure game: difficulty and fleet selection.",
                enter_new_game_setup=True,
            )
        if trigger == "to_create_preset" and next_state is AppState.PLACEMENT_EDIT:
            return AppTransition(
                state=AppState.PLACEMENT_EDIT,
                status="Drag a ship from panel, drop onto board. Press R while holding to rotate.",
                reset_editor=True,
                clear_editing_preset_name=True,
            )
        if trigger == "to_main_menu" and next_state is AppState.MAIN_MENU:
            return AppTransition(
                state=AppState.MAIN_MENU,
                status="Choose New Game, Manage Presets, or Quit.",
                clear_session=True,
            )
        if trigger == "to_back_to_presets" and next_state is AppState.PRESET_MANAGE:
            return AppTransition(
                state=AppState.PRESET_MANAGE,
                status="Manage presets.",
                refresh_preset_rows=True,
            )
        return None

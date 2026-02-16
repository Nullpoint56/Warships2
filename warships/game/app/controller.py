"""Application controller for state transitions and game flow."""

from __future__ import annotations

import logging
import random

from warships.game.app.controller_state import ControllerState
from warships.game.app.events import (
    BoardCellPressed,
    ButtonPressed,
    CharTyped,
    KeyPressed,
    PointerMoved,
    PointerReleased,
)
from warships.game.app.ports.runtime_primitives import GridLayout
from warships.game.app.ports.runtime_services import ActionDispatcher, apply_wheel_scroll
from warships.game.app.services.battle import resolve_player_turn, start_game
from warships.game.app.services.controller_support import ControllerSupport
from warships.game.app.services.input_policy import (
    can_handle_key_for_placement,
    can_handle_pointer_down,
    can_handle_pointer_move,
    can_handle_pointer_release,
    pointer_down_action,
    resolve_wheel_target,
)
from warships.game.app.services.mutation_orchestration import (
    apply_battle_turn_outcome,
    apply_edit_preset_result,
    apply_placement_outcome,
)
from warships.game.app.services.new_game_flow import NewGameFlowService
from warships.game.app.services.placement_editor import PlacementEditorService
from warships.game.app.services.placement_flow import HeldShipState, PlacementFlowService
from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.app.services.prompt_flow import PromptFlowService
from warships.game.app.services.prompt_orchestration import (
    apply_prompt_confirm_outcome,
    apply_prompt_interaction_outcome,
)
from warships.game.app.services.session_flow import AppTransition, SessionFlowService
from warships.game.app.services.setup_orchestration import (
    refresh_preset_state,
    resolve_new_game_selection,
)
from warships.game.app.services.state_projection import build_ui_state
from warships.game.app.services.transition_orchestration import apply_transition
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.core.fleet import random_fleet
from warships.game.core.models import ShipPlacement, ShipType
from warships.game.presets.service import PresetService
from warships.game.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL

_SHIP_ORDER = [
    ShipType.CARRIER,
    ShipType.BATTLESHIP,
    ShipType.CRUISER,
    ShipType.SUBMARINE,
    ShipType.DESTROYER,
]

logger = logging.getLogger(__name__)
_GRID_LAYOUT = GridLayout()
_NEW_GAME_VISIBLE_PRESET_ROWS = NEW_GAME_SETUP.visible_row_capacity()
_PRESET_MANAGE_VISIBLE_ROWS = PRESET_PANEL.visible_row_capacity()


class GameController:
    """Handles app events and owns editor state."""

    def __init__(
        self, preset_service: PresetService, rng: random.Random, debug_ui: bool = False
    ) -> None:
        self._preset_service = preset_service
        self._rng = rng

        self._state_data = ControllerState(
            placements_by_type={ship_type: None for ship_type in _SHIP_ORDER},
        )
        self._support = ControllerSupport(
            state=self._state_data,
            ship_order=list(_SHIP_ORDER),
            new_game_visible_rows=_NEW_GAME_VISIBLE_PRESET_ROWS,
            preset_manage_visible_rows=_PRESET_MANAGE_VISIBLE_ROWS,
            logger=logger,
            debug_ui=debug_ui,
        )
        self._button_dispatcher = ActionDispatcher(
            direct_handlers={
                "manage_presets": self._on_manage_presets,
                "new_game": self._on_new_game,
                "create_preset": self._on_create_preset,
                "back_main": self._on_back_main,
                "new_game_toggle_difficulty": self._on_toggle_new_game_difficulty,
                "new_game_randomize": self._on_new_game_randomize,
                "start_game": self._start_game,
                "quit": self._on_quit,
                "play_again": self._on_play_again,
                "back_to_presets": self._on_back_to_presets,
                "save_preset": self._on_save_preset,
                "randomize": self._randomize_editor,
            },
            prefixed_handlers=(
                ("new_game_diff_option:", self._on_new_game_diff_option),
                ("new_game_select_preset:", self._select_new_game_preset),
                ("preset_edit:", self._edit_preset),
                ("preset_rename:", self._on_preset_rename),
                ("preset_delete:", self._on_preset_delete),
            ),
        )
        self._refresh_preset_rows()
        self._refresh_buttons()
        self._announce_state()

    def ui_state(self) -> AppUIState:
        """Return current view-ready state."""
        return build_ui_state(
            state=self._state_data.app_state,
            status=self._state_data.status,
            buttons=self._state_data.buttons,
            placements_by_type=self._state_data.placements_by_type,
            held_orientation=self._state_data.held_orientation,
            session=self._state_data.session,
            ship_order=list(_SHIP_ORDER),
            is_closing=self._state_data.is_closing,
            preset_rows=self._state_data.preset_rows,
            preset_manage_scroll=self._state_data.preset_manage_scroll,
            preset_manage_visible_rows=_PRESET_MANAGE_VISIBLE_ROWS,
            prompt=self._state_data.prompt_state.prompt,
            held_ship_type=self._state_data.held_ship_type,
            held_ship_orientation=self._state_data.held_orientation,
            held_grab_index=self._state_data.held_grab_index,
            hover_cell=self._state_data.hover_cell,
            hover_x=self._state_data.hover_x,
            hover_y=self._state_data.hover_y,
            new_game_difficulty=self._current_difficulty(),
            new_game_difficulty_open=self._state_data.new_game_difficulty_open,
            new_game_preset_scroll=self._state_data.new_game_preset_scroll,
            new_game_visible_rows=_NEW_GAME_VISIBLE_PRESET_ROWS,
            new_game_selected_preset=self._state_data.new_game_selected_preset,
            new_game_source=self._state_data.new_game_source_label,
            new_game_preview=self._state_data.new_game_preview,
        )

    def handle_button(self, event: ButtonPressed) -> bool:
        """Process button event. Returns whether UI changed."""
        button_id = event.button_id
        if self._state_data.prompt_state.prompt is not None:
            return self._handle_prompt_button(button_id)
        handled = self._button_dispatcher.dispatch(button_id)
        return handled if handled is not None else False

    def _on_manage_presets(self) -> bool:
        self._apply_transition(SessionFlowService.to_manage_presets())
        return True

    def _on_new_game(self) -> bool:
        self._apply_transition(SessionFlowService.to_new_game_setup())
        return True

    def _on_create_preset(self) -> bool:
        self._apply_transition(SessionFlowService.to_create_preset())
        return True

    def _on_back_main(self) -> bool:
        self._apply_transition(SessionFlowService.to_main_menu())
        return True

    def _on_toggle_new_game_difficulty(self) -> bool:
        self._state_data.new_game_difficulty_open = not self._state_data.new_game_difficulty_open
        self._refresh_buttons()
        return True

    def _on_new_game_diff_option(self, diff: str) -> bool:
        new_index, status = NewGameFlowService.choose_difficulty(
            self._state_data.new_game_difficulty_index, diff
        )
        if status is None:
            return False
        self._state_data.new_game_difficulty_index = new_index
        self._state_data.new_game_difficulty_open = False
        self._set_status(status)
        self._refresh_buttons()
        return True

    def _on_new_game_randomize(self) -> bool:
        selection = NewGameFlowService.randomize_selection(self._rng)
        self._apply_new_game_selection_state(
            selected_preset=selection.selected_preset,
            random_fleet=selection.random_fleet,
            preview=selection.preview,
            source_label=selection.source_label,
        )
        self._set_status(selection.status or self._state_data.status)
        return True

    def _on_quit(self) -> bool:
        self._state_data.is_closing = True
        return True

    def _on_play_again(self) -> bool:
        self._apply_transition(SessionFlowService.to_new_game_setup())
        return True

    def _on_back_to_presets(self) -> bool:
        self._apply_transition(SessionFlowService.to_back_to_presets())
        return True

    def _on_save_preset(self) -> bool:
        if not PlacementEditorService.all_ships_placed(
            self._state_data.placements_by_type, _SHIP_ORDER
        ):
            self._set_status("Place all ships before saving.")
            return True
        default_name = self._state_data.editing_preset_name or "new_preset"
        self._state_data.prompt_state = PromptFlowService.open_prompt(
            "Save Preset", default_name, mode="save"
        )
        self._refresh_buttons()
        return True

    def _on_preset_rename(self, name: str) -> bool:
        self._state_data.prompt_state = PromptFlowService.open_prompt(
            "Rename Preset", name, mode="rename", target=name
        )
        self._refresh_buttons()
        return True

    def _on_preset_delete(self, name: str) -> bool:
        self._preset_service.delete_preset(name)
        self._set_status(f"Deleted preset '{name}'.")
        self._refresh_preset_rows()
        self._refresh_buttons()
        return True

    def handle_board_click(self, event: BoardCellPressed) -> bool:
        """Handle board click for battle firing."""
        if (
            self._state_data.app_state is not AppState.BATTLE
            or self._state_data.session is None
            or self._state_data.ai_strategy is None
        ):
            return False
        if not event.is_ai_board:
            return False
        turn = resolve_player_turn(
            self._state_data.session, self._state_data.ai_strategy, event.coord
        )
        apply_battle_turn_outcome(
            turn,
            state=self._state_data,
            refresh_buttons=self._refresh_buttons,
        )
        return True

    def handle_pointer_move(self, event: PointerMoved) -> bool:
        """Update hover cell while dragging in editor."""
        if not can_handle_pointer_move(self._state_data.app_state):
            return False
        self._state_data.hover_x = event.x
        self._state_data.hover_y = event.y
        self._state_data.hover_cell = PlacementEditorService.to_primary_grid_cell(
            _GRID_LAYOUT, event.x, event.y
        )
        return self._state_data.held_ship_type is not None

    def handle_pointer_release(self, event: PointerReleased) -> bool:
        """Drop held ship on pointer release."""
        if not can_handle_pointer_release(self._state_data.app_state, event.button):
            return False
        outcome = PlacementFlowService.on_pointer_release(
            placements_by_type=self._state_data.placements_by_type,
            held_state=self._held_state(),
            layout=_GRID_LAYOUT,
            x=event.x,
            y=event.y,
        )
        return apply_placement_outcome(
            outcome,
            state=self._state_data,
            refresh_buttons=self._refresh_buttons,
        )

    def handle_key_pressed(self, event: KeyPressed) -> bool:
        """Handle key-down events for prompt and placement rotation."""
        key = event.key.lower()
        if self._state_data.prompt_state.prompt is not None:
            prompt_outcome = PromptFlowService.handle_key(self._state_data.prompt_state, key)
            return apply_prompt_interaction_outcome(
                prompt_outcome,
                state=self._state_data,
                confirm_prompt=self._confirm_prompt,
                refresh_buttons=self._refresh_buttons,
            )

        if can_handle_key_for_placement(self._state_data.app_state):
            placement_outcome = PlacementFlowService.on_key_for_held(
                key=key, held_state=self._held_state()
            )
            if placement_outcome.handled:
                return apply_placement_outcome(
                    placement_outcome,
                    state=self._state_data,
                    refresh_buttons=self._refresh_buttons,
                )
        return False

    def handle_char_typed(self, event: CharTyped) -> bool:
        """Handle text input for prompt."""
        outcome = PromptFlowService.handle_char(self._state_data.prompt_state, event.char)
        if not outcome.handled:
            return False
        self._state_data.prompt_state = outcome.state
        return True

    def handle_wheel(self, x: float, y: float, dy: float) -> bool:
        """Handle mouse wheel interactions."""
        target = resolve_wheel_target(self._state_data.app_state, x, y)
        if target == "preset_manage":
            return self.scroll_preset_manage_rows(dy)
        if target == "new_game_presets":
            return self.scroll_new_game_presets(dy)
        return False

    def scroll_new_game_presets(self, dy: float) -> bool:
        """Scroll the new-game preset list by wheel delta semantics."""
        if self._state_data.app_state is not AppState.NEW_GAME_SETUP:
            return False
        outcome = apply_wheel_scroll(
            dy=dy,
            current_scroll=self._state_data.new_game_preset_scroll,
            can_scroll_down=PresetFlowService.can_scroll_down(
                self._state_data.preset_rows,
                self._state_data.new_game_preset_scroll,
                _NEW_GAME_VISIBLE_PRESET_ROWS,
            ),
        )
        if outcome.handled:
            self._state_data.new_game_preset_scroll = outcome.next_scroll
            self._refresh_buttons()
            return True
        return False

    def scroll_preset_manage_rows(self, dy: float) -> bool:
        """Scroll preset manager rows by wheel delta semantics."""
        if self._state_data.app_state is not AppState.PRESET_MANAGE:
            return False
        outcome = apply_wheel_scroll(
            dy=dy,
            current_scroll=self._state_data.preset_manage_scroll,
            can_scroll_down=self._preset_manage_can_scroll_down(),
        )
        if outcome.handled:
            self._state_data.preset_manage_scroll = outcome.next_scroll
            self._refresh_buttons()
            return True
        return False

    def submit_prompt_text(self, text: str) -> bool:
        """Set current prompt text and confirm it."""
        if self._state_data.prompt_state.prompt is None:
            return False
        self._state_data.prompt_state = PromptFlowService.sync_prompt(
            self._state_data.prompt_state, text[:32]
        )
        return self._confirm_prompt()

    def cancel_prompt(self) -> bool:
        """Cancel currently open prompt."""
        if self._state_data.prompt_state.prompt is None:
            return False
        self._state_data.prompt_state = PromptFlowService.close_prompt()
        self._refresh_buttons()
        return True

    def handle_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Pick ship from board or palette."""
        if not can_handle_pointer_down(
            self._state_data.app_state, has_prompt=self._state_data.prompt_state.prompt is not None
        ):
            return False
        action = pointer_down_action(button)
        if action is None:
            return False
        if action == "right":
            outcome = PlacementFlowService.on_right_pointer_down(
                placements_by_type=self._state_data.placements_by_type,
                held_state=self._held_state(),
                layout=_GRID_LAYOUT,
                x=x,
                y=y,
            )
            return apply_placement_outcome(
                outcome,
                state=self._state_data,
                refresh_buttons=self._refresh_buttons,
            )

        self._state_data.hover_x = x
        self._state_data.hover_y = y
        outcome = PlacementFlowService.on_left_pointer_down(
            ship_order=_SHIP_ORDER,
            placements_by_type=self._state_data.placements_by_type,
            held_state=self._held_state(),
            layout=_GRID_LAYOUT,
            x=x,
            y=y,
        )
        return apply_placement_outcome(
            outcome,
            state=self._state_data,
            refresh_buttons=self._refresh_buttons,
        )

    def _handle_prompt_button(self, button_id: str) -> bool:
        outcome = PromptFlowService.handle_button(self._state_data.prompt_state, button_id)
        return apply_prompt_interaction_outcome(
            outcome,
            state=self._state_data,
            confirm_prompt=self._confirm_prompt,
            refresh_buttons=self._refresh_buttons,
        )

    def _confirm_prompt(self) -> bool:
        outcome = PromptFlowService.confirm(
            mode=self._state_data.prompt_state.mode,
            value=self._state_data.prompt_state.buffer,
            prompt_target=self._state_data.prompt_state.target,
            pending_save_name=self._state_data.pending_save_name,
            editing_preset_name=self._state_data.editing_preset_name,
            preset_names=[row.name for row in self._state_data.preset_rows],
            placements=PlacementEditorService.placements_list(self._state_data.placements_by_type),
            preset_service=self._preset_service,
        )
        return apply_prompt_confirm_outcome(
            outcome,
            state=self._state_data,
            refresh_preset_rows=self._refresh_preset_rows,
            refresh_buttons=self._refresh_buttons,
            announce_state=self._announce_state,
        )

    def _edit_preset(self, name: str) -> bool:
        result = PresetFlowService.load_preset_for_edit(self._preset_service, name)
        return apply_edit_preset_result(
            result,
            preset_name=name,
            state=self._state_data,
            reset_editor=self._reset_editor,
            apply_placements=self._apply_loaded_placements,
            refresh_buttons=self._refresh_buttons,
            announce_state=self._announce_state,
        )

    def _reset_editor(self) -> None:
        self._support.reset_editor()

    def _held_state(self) -> HeldShipState:
        return HeldShipState(
            ship_type=self._state_data.held_ship_type,
            orientation=self._state_data.held_orientation,
            previous=self._state_data.held_previous,
            grab_index=self._state_data.held_grab_index,
        )

    def _apply_transition(self, transition: AppTransition) -> None:
        apply_transition(
            transition,
            state=self._state_data,
            reset_editor=self._reset_editor,
            enter_new_game_setup=self._enter_new_game_setup,
            refresh_preset_rows=self._refresh_preset_rows,
            refresh_buttons=self._refresh_buttons,
            announce_state=self._announce_state,
        )

    def _randomize_editor(self) -> bool:
        self._reset_editor()
        for placement in random_fleet(self._rng).ships:
            self._state_data.placements_by_type[placement.ship_type] = placement
        self._state_data.status = "Placement randomized."
        self._refresh_buttons()
        return True

    def _current_difficulty(self) -> str:
        return NewGameFlowService.current_difficulty(self._state_data.new_game_difficulty_index)

    def _enter_new_game_setup(self) -> None:
        self._refresh_preset_rows()
        self._state_data.new_game_difficulty_open = False
        self._state_data.new_game_preset_scroll = 0
        self._state_data.new_game_random_fleet = None
        selection = resolve_new_game_selection(
            preset_service=self._preset_service,
            preset_rows=self._state_data.preset_rows,
        )
        self._apply_new_game_selection_state(
            selected_preset=selection.selected_preset,
            random_fleet=selection.random_fleet,
            preview=selection.preview,
            source_label=selection.source_label,
        )

    def _select_new_game_preset(self, name: str) -> bool:
        selection = NewGameFlowService.select_preset(self._preset_service, name)
        self._apply_new_game_selection_state(
            selected_preset=selection.selected_preset,
            random_fleet=selection.random_fleet,
            preview=selection.preview,
            source_label=selection.source_label,
        )
        if selection.status is not None:
            self._set_status(selection.status)
        return True

    def _start_game(self) -> bool:
        result = start_game(
            preset_service=self._preset_service,
            rng=self._rng,
            difficulty=self._current_difficulty(),
            selected_preset=self._state_data.new_game_selected_preset,
            random_fleet_choice=self._state_data.new_game_random_fleet,
        )
        if not result.success or result.session is None or result.ai_strategy is None:
            self._set_status(result.status)
            return True
        self._state_data.session = result.session
        self._state_data.ai_strategy = result.ai_strategy
        self._apply_transition(
            AppTransition(
                state=AppState.BATTLE,
                status=result.status,
                refresh_buttons=True,
                announce_state=True,
            )
        )
        return True

    def _refresh_preset_rows(self) -> None:
        result = refresh_preset_state(
            preset_service=self._preset_service,
            selected_preset=self._state_data.new_game_selected_preset,
            new_game_scroll=self._state_data.new_game_preset_scroll,
            preset_manage_scroll=self._state_data.preset_manage_scroll,
            new_game_visible_rows=_NEW_GAME_VISIBLE_PRESET_ROWS,
            preset_manage_visible_rows=_PRESET_MANAGE_VISIBLE_ROWS,
            logger=logger,
        )
        self._state_data.preset_rows = result.rows
        self._state_data.new_game_selected_preset = result.selected_preset
        self._state_data.new_game_preset_scroll = result.new_game_scroll
        self._state_data.preset_manage_scroll = result.preset_manage_scroll

    def _apply_new_game_selection_state(
        self,
        *,
        selected_preset: str | None,
        random_fleet,
        preview: list[ShipPlacement],
        source_label: str | None,
    ) -> None:
        self._support.apply_new_game_selection(
            selected_preset=selected_preset,
            random_fleet=random_fleet,
            preview=preview,
            source_label=source_label,
        )

    def _set_status(self, status: str) -> None:
        self._support.set_status(status)

    def _apply_loaded_placements(self, placements: list[ShipPlacement]) -> None:
        self._support.apply_loaded_placements(placements)

    def _refresh_buttons(self) -> None:
        self._support.refresh_buttons()

    def _preset_manage_can_scroll_down(self) -> bool:
        return self._support.preset_manage_can_scroll_down()

    def _announce_state(self) -> None:
        self._support.announce_state()

"""Application controller for state transitions and game flow."""

from __future__ import annotations

from collections.abc import Callable
import logging
import random

from warships.ai.strategy import AIStrategy
from warships.app.services.battle import resolve_player_turn, start_game
from warships.app.services.menu_scroll import MenuScrollService
from warships.app.services.new_game_flow import DIFFICULTIES, NewGameFlowService
from warships.app.services.placement_editor import PlacementEditorService
from warships.app.services.placement_flow import HeldShipState, PlacementFlowService
from warships.app.services.preset_flow import PresetFlowService
from warships.app.services.prompt_flow import PromptFlowService, PromptState
from warships.app.services.session_flow import AppTransition, SessionFlowService
from warships.app.services.ui_buttons import new_game_setup_buttons, preset_row_buttons, prompt_buttons
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState, PresetRowView
from warships.core.fleet import random_fleet
from warships.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType
from warships.core.rules import GameSession
from warships.engine.ui_runtime.board_layout import BoardLayout
from warships.presets.service import PresetService
from warships.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL
from warships.ui.overlays import Button, buttons_for_state

_SHIP_ORDER = [
    ShipType.CARRIER,
    ShipType.BATTLESHIP,
    ShipType.CRUISER,
    ShipType.SUBMARINE,
    ShipType.DESTROYER,
]

logger = logging.getLogger(__name__)
_BOARD_LAYOUT = BoardLayout()
_NEW_GAME_VISIBLE_PRESET_ROWS = NEW_GAME_SETUP.visible_row_capacity()
_PRESET_MANAGE_VISIBLE_ROWS = PRESET_PANEL.visible_row_capacity()


class GameController:
    """Handles app events and owns editor state."""

    def __init__(self, preset_service: PresetService, rng: random.Random, debug_ui: bool = False) -> None:
        self._preset_service = preset_service
        self._rng = rng
        self._debug_ui = debug_ui

        self._state = AppState.MAIN_MENU
        self._status = "Choose New Game, Manage Presets, or Quit."
        self._is_closing = False
        self._session: GameSession | None = None
        self._ai_strategy: AIStrategy | None = None

        self._placements_by_type: dict[ShipType, ShipPlacement | None] = {ship_type: None for ship_type in _SHIP_ORDER}
        self._held_ship_type: ShipType | None = None
        self._held_orientation: Orientation | None = None
        self._held_previous: ShipPlacement | None = None
        self._held_grab_index: int = 0
        self._hover_cell: Coord | None = None
        self._hover_x: float | None = None
        self._hover_y: float | None = None

        self._preset_rows: list[PresetRowView] = []
        self._preset_manage_scroll = 0
        self._editing_preset_name: str | None = None
        self._new_game_difficulty_index = 1
        self._new_game_difficulty_open = False
        self._new_game_selected_preset: str | None = None
        self._new_game_preset_scroll = 0
        self._new_game_random_fleet: FleetPlacement | None = None
        self._new_game_preview: list[ShipPlacement] = []
        self._new_game_source_label: str | None = None

        self._prompt_state = PromptState()
        self._pending_save_name: str | None = None

        self._buttons: list[Button] = []
        self._button_handlers: dict[str, Callable[[], bool]] = {
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
        }
        self._prefixed_button_handlers: list[tuple[str, Callable[[str], bool]]] = [
            ("new_game_diff_option:", self._on_new_game_diff_option),
            ("new_game_select_preset:", self._select_new_game_preset),
            ("preset_edit:", self._edit_preset),
            ("preset_rename:", self._on_preset_rename),
            ("preset_delete:", self._on_preset_delete),
        ]
        self._refresh_preset_rows()
        self._refresh_buttons()
        self._announce_state()

    def ui_state(self) -> AppUIState:
        """Return current view-ready state."""
        return AppUIState(
            state=self._state,
            status=self._status,
            buttons=self._buttons,
            placements=PlacementEditorService.placements_list(self._placements_by_type),
            placement_orientation=self._held_orientation or Orientation.HORIZONTAL,
            session=self._session,
            ship_order=list(_SHIP_ORDER),
            is_closing=self._is_closing,
            preset_rows=self._visible_preset_manage_rows(),
            prompt=self._prompt_state.prompt,
            held_ship_type=self._held_ship_type,
            held_ship_orientation=self._held_orientation,
            held_grab_index=self._held_grab_index,
            hover_cell=self._hover_cell,
            hover_x=self._hover_x,
            hover_y=self._hover_y,
            new_game_difficulty=self._current_difficulty(),
            new_game_difficulty_open=self._new_game_difficulty_open,
            new_game_difficulty_options=list(DIFFICULTIES),
            new_game_visible_presets=PresetFlowService.visible_new_game_preset_names(
                self._preset_rows, self._new_game_preset_scroll, _NEW_GAME_VISIBLE_PRESET_ROWS
            ),
            new_game_selected_preset=self._new_game_selected_preset,
            new_game_can_scroll_up=self._new_game_preset_scroll > 0,
            new_game_can_scroll_down=PresetFlowService.can_scroll_down(
                self._preset_rows, self._new_game_preset_scroll, _NEW_GAME_VISIBLE_PRESET_ROWS
            ),
            new_game_source=self._new_game_source_label,
            new_game_preview=list(self._new_game_preview),
            preset_manage_can_scroll_up=self._preset_manage_scroll > 0,
            preset_manage_can_scroll_down=self._preset_manage_can_scroll_down(),
        )

    def handle_button(self, event: ButtonPressed) -> bool:
        """Process button event. Returns whether UI changed."""
        button_id = event.button_id
        if self._prompt_state.prompt is not None:
            return self._handle_prompt_button(button_id)
        handler = self._button_handlers.get(button_id)
        if handler is not None:
            return handler()
        for prefix, prefixed_handler in self._prefixed_button_handlers:
            if button_id.startswith(prefix):
                suffix = button_id.split(":", 1)[1]
                return prefixed_handler(suffix)
        return False

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
        self._new_game_difficulty_open = not self._new_game_difficulty_open
        self._refresh_buttons()
        return True

    def _on_new_game_diff_option(self, diff: str) -> bool:
        new_index, status = NewGameFlowService.choose_difficulty(self._new_game_difficulty_index, diff)
        if status is None:
            return False
        self._new_game_difficulty_index = new_index
        self._new_game_difficulty_open = False
        self._status = status
        self._refresh_buttons()
        return True

    def _on_new_game_randomize(self) -> bool:
        selection = NewGameFlowService.randomize_selection(self._rng)
        self._new_game_selected_preset = selection.selected_preset
        self._new_game_random_fleet = selection.random_fleet
        self._new_game_preview = selection.preview
        self._new_game_source_label = selection.source_label
        self._status = selection.status or self._status
        return True

    def _on_quit(self) -> bool:
        self._is_closing = True
        return True

    def _on_play_again(self) -> bool:
        self._apply_transition(SessionFlowService.to_new_game_setup())
        return True

    def _on_back_to_presets(self) -> bool:
        self._apply_transition(SessionFlowService.to_back_to_presets())
        return True

    def _on_save_preset(self) -> bool:
        if not PlacementEditorService.all_ships_placed(self._placements_by_type, _SHIP_ORDER):
            self._status = "Place all ships before saving."
            return True
        default_name = self._editing_preset_name or "new_preset"
        self._prompt_state = PromptFlowService.open_prompt("Save Preset", default_name, mode="save")
        self._refresh_buttons()
        return True

    def _on_preset_rename(self, name: str) -> bool:
        self._prompt_state = PromptFlowService.open_prompt("Rename Preset", name, mode="rename", target=name)
        self._refresh_buttons()
        return True

    def _on_preset_delete(self, name: str) -> bool:
        self._preset_service.delete_preset(name)
        self._status = f"Deleted preset '{name}'."
        self._refresh_preset_rows()
        self._refresh_buttons()
        return True

    def handle_board_click(self, event: BoardCellPressed) -> bool:
        """Handle board click for battle firing."""
        if self._state is not AppState.BATTLE or self._session is None or self._ai_strategy is None:
            return False
        if not event.is_ai_board:
            return False
        turn = resolve_player_turn(self._session, self._ai_strategy, event.coord)
        self._status = turn.status
        if turn.winner is not None:
            self._state = AppState.RESULT
            self._refresh_buttons()
        return True

    def handle_pointer_move(self, event: PointerMoved) -> bool:
        """Update hover cell while dragging in editor."""
        if self._state is not AppState.PLACEMENT_EDIT:
            return False
        self._hover_x = event.x
        self._hover_y = event.y
        self._hover_cell = PlacementEditorService.to_board_cell(_BOARD_LAYOUT, event.x, event.y)
        return self._held_ship_type is not None

    def handle_pointer_release(self, event: PointerReleased) -> bool:
        """Drop held ship on pointer release."""
        if self._state is not AppState.PLACEMENT_EDIT:
            return False
        if event.button != 1:
            return False
        outcome = PlacementFlowService.on_pointer_release(
            placements_by_type=self._placements_by_type,
            held_state=self._held_state(),
            layout=_BOARD_LAYOUT,
            x=event.x,
            y=event.y,
        )
        if not outcome.handled:
            return False
        self._set_held_state(outcome.held_state)
        if outcome.status is not None:
            self._status = outcome.status
        if outcome.refresh_buttons:
            self._refresh_buttons()
        return True

    def handle_key_pressed(self, event: KeyPressed) -> bool:
        """Handle key-down events for prompt and placement rotation."""
        key = event.key.lower()
        if self._prompt_state.prompt is not None:
            outcome = PromptFlowService.handle_key(self._prompt_state, key)
            if not outcome.handled:
                return False
            self._prompt_state = outcome.state
            if outcome.request_confirm:
                return self._confirm_prompt()
            if outcome.refresh_buttons:
                self._refresh_buttons()
            return True

        if self._state is AppState.PLACEMENT_EDIT:
            outcome = PlacementFlowService.on_key_for_held(key=key, held_state=self._held_state())
            if outcome.handled:
                self._set_held_state(outcome.held_state)
                if outcome.status is not None:
                    self._status = outcome.status
                if outcome.refresh_buttons:
                    self._refresh_buttons()
                return True
        return False

    def handle_char_typed(self, event: CharTyped) -> bool:
        """Handle text input for prompt."""
        outcome = PromptFlowService.handle_char(self._prompt_state, event.char)
        if not outcome.handled:
            return False
        self._prompt_state = outcome.state
        return True

    def handle_wheel(self, x: float, y: float, dy: float) -> bool:
        """Handle mouse wheel interactions."""
        if self._state is not AppState.NEW_GAME_SETUP:
            if self._state is not AppState.PRESET_MANAGE:
                return False
            panel_rect = PRESET_PANEL.panel_rect()
            if not panel_rect.contains(x, y):
                return False
            return self.scroll_preset_manage_rows(dy)
        list_rect = NEW_GAME_SETUP.preset_list_rect()
        if not list_rect.contains(x, y):
            return False
        return self.scroll_new_game_presets(dy)

    def scroll_new_game_presets(self, dy: float) -> bool:
        """Scroll the new-game preset list by wheel delta semantics."""
        if self._state is not AppState.NEW_GAME_SETUP:
            return False
        outcome = MenuScrollService.apply(
            dy=dy,
            current_scroll=self._new_game_preset_scroll,
            can_scroll_down=PresetFlowService.can_scroll_down(
                self._preset_rows, self._new_game_preset_scroll, _NEW_GAME_VISIBLE_PRESET_ROWS
            ),
        )
        if outcome.handled:
            self._new_game_preset_scroll = outcome.next_scroll
            self._refresh_buttons()
            return True
        return False

    def scroll_preset_manage_rows(self, dy: float) -> bool:
        """Scroll preset manager rows by wheel delta semantics."""
        if self._state is not AppState.PRESET_MANAGE:
            return False
        outcome = MenuScrollService.apply(
            dy=dy,
            current_scroll=self._preset_manage_scroll,
            can_scroll_down=self._preset_manage_can_scroll_down(),
        )
        if outcome.handled:
            self._preset_manage_scroll = outcome.next_scroll
            self._refresh_buttons()
            return True
        return False

    def submit_prompt_text(self, text: str) -> bool:
        """Set current prompt text and confirm it."""
        if self._prompt_state.prompt is None:
            return False
        self._prompt_state = PromptFlowService.sync_prompt(self._prompt_state, text[:32])
        return self._confirm_prompt()

    def cancel_prompt(self) -> bool:
        """Cancel currently open prompt."""
        if self._prompt_state.prompt is None:
            return False
        self._prompt_state = PromptFlowService.close_prompt()
        self._refresh_buttons()
        return True

    def handle_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Pick ship from board or palette."""
        if self._state is not AppState.PLACEMENT_EDIT or self._prompt_state.prompt is not None:
            return False
        if button == 2:
            outcome = PlacementFlowService.on_right_pointer_down(
                placements_by_type=self._placements_by_type,
                held_state=self._held_state(),
                layout=_BOARD_LAYOUT,
                x=x,
                y=y,
            )
            if not outcome.handled:
                return False
            self._set_held_state(outcome.held_state)
            if outcome.status is not None:
                self._status = outcome.status
            if outcome.refresh_buttons:
                self._refresh_buttons()
            return True
        if button != 1:
            return False

        self._hover_x = x
        self._hover_y = y
        outcome = PlacementFlowService.on_left_pointer_down(
            ship_order=_SHIP_ORDER,
            placements_by_type=self._placements_by_type,
            held_state=self._held_state(),
            layout=_BOARD_LAYOUT,
            x=x,
            y=y,
        )
        if not outcome.handled:
            return False
        self._set_held_state(outcome.held_state)
        if outcome.status is not None:
            self._status = outcome.status
        if outcome.refresh_buttons:
            self._refresh_buttons()
        return True

    def _handle_prompt_button(self, button_id: str) -> bool:
        outcome = PromptFlowService.handle_button(self._prompt_state, button_id)
        if not outcome.handled:
            return False
        self._prompt_state = outcome.state
        if outcome.request_confirm:
            return self._confirm_prompt()
        if outcome.refresh_buttons:
            self._refresh_buttons()
        return True

    def _confirm_prompt(self) -> bool:
        outcome = PromptFlowService.confirm(
            mode=self._prompt_state.mode,
            value=self._prompt_state.buffer,
            prompt_target=self._prompt_state.target,
            pending_save_name=self._pending_save_name,
            editing_preset_name=self._editing_preset_name,
            preset_names=[row.name for row in self._preset_rows],
            placements=PlacementEditorService.placements_list(self._placements_by_type),
            preset_service=self._preset_service,
        )
        if not outcome.handled:
            return False
        if outcome.status is not None:
            self._status = outcome.status
        self._pending_save_name = outcome.pending_save_name
        self._editing_preset_name = outcome.editing_preset_name
        self._prompt_state = PromptState(
            prompt=outcome.prompt,
            buffer=outcome.prompt_buffer,
            mode=outcome.prompt_mode,
            target=outcome.prompt_target,
        )
        if outcome.switch_to_preset_manage:
            self._state = AppState.PRESET_MANAGE
        if outcome.refresh_preset_rows:
            self._refresh_preset_rows()
        if outcome.refresh_buttons:
            self._refresh_buttons()
        if outcome.announce_state:
            self._announce_state()
        return True

    def _edit_preset(self, name: str) -> bool:
        result = PresetFlowService.load_preset_for_edit(self._preset_service, name)
        if not result.success:
            self._status = result.status
            return True
        self._state = AppState.PLACEMENT_EDIT
        self._reset_editor()
        for placement in result.placements:
            self._placements_by_type[placement.ship_type] = placement
        self._editing_preset_name = name
        self._status = result.status
        self._refresh_buttons()
        self._announce_state()
        return True

    def _reset_editor(self) -> None:
        self._placements_by_type = PlacementEditorService.reset(_SHIP_ORDER)
        self._held_ship_type = None
        self._held_orientation = None
        self._held_previous = None
        self._held_grab_index = 0
        self._hover_cell = None
        self._hover_x = None
        self._hover_y = None

    def _held_state(self) -> HeldShipState:
        return HeldShipState(
            ship_type=self._held_ship_type,
            orientation=self._held_orientation,
            previous=self._held_previous,
            grab_index=self._held_grab_index,
        )

    def _set_held_state(self, state: HeldShipState) -> None:
        self._held_ship_type = state.ship_type
        self._held_orientation = state.orientation
        self._held_previous = state.previous
        self._held_grab_index = state.grab_index

    def _apply_transition(self, transition: AppTransition) -> None:
        self._state = transition.state
        self._status = transition.status
        if transition.clear_session:
            self._session = None
        if transition.reset_editor:
            self._reset_editor()
        if transition.clear_editing_preset_name:
            self._editing_preset_name = None
        if transition.enter_new_game_setup:
            self._enter_new_game_setup()
        if transition.refresh_preset_rows:
            self._refresh_preset_rows()
        if transition.refresh_buttons:
            self._refresh_buttons()
        if transition.announce_state:
            self._announce_state()

    def _randomize_editor(self) -> bool:
        self._reset_editor()
        for placement in random_fleet(self._rng).ships:
            self._placements_by_type[placement.ship_type] = placement
        self._status = "Placement randomized."
        self._refresh_buttons()
        return True

    def _current_difficulty(self) -> str:
        return NewGameFlowService.current_difficulty(self._new_game_difficulty_index)

    def _enter_new_game_setup(self) -> None:
        self._refresh_preset_rows()
        self._new_game_difficulty_open = False
        self._new_game_preset_scroll = 0
        self._new_game_random_fleet = None
        default_name = NewGameFlowService.default_selection(self._preset_rows)
        if default_name is not None:
            self._select_new_game_preset(default_name)
        else:
            self._new_game_selected_preset = None
            self._new_game_preview = []
            self._new_game_source_label = None

    def _select_new_game_preset(self, name: str) -> bool:
        selection = NewGameFlowService.select_preset(self._preset_service, name)
        self._new_game_selected_preset = selection.selected_preset
        self._new_game_random_fleet = selection.random_fleet
        self._new_game_preview = selection.preview
        self._new_game_source_label = selection.source_label
        if selection.status is not None:
            self._status = selection.status
        return True

    def _start_game(self) -> bool:
        result = start_game(
            preset_service=self._preset_service,
            rng=self._rng,
            difficulty=self._current_difficulty(),
            selected_preset=self._new_game_selected_preset,
            random_fleet_choice=self._new_game_random_fleet,
        )
        if not result.success or result.session is None or result.ai_strategy is None:
            self._status = result.status
            return True
        self._session = result.session
        self._ai_strategy = result.ai_strategy
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
        result = PresetFlowService.refresh_rows(
            preset_service=self._preset_service,
            selected_preset=self._new_game_selected_preset,
            scroll=self._new_game_preset_scroll,
            visible_rows=_NEW_GAME_VISIBLE_PRESET_ROWS,
            logger=logger,
        )
        self._preset_rows = result.rows
        self._new_game_selected_preset = result.selected_preset
        self._new_game_preset_scroll = result.scroll
        max_manage_scroll = max(0, len(self._preset_rows) - _PRESET_MANAGE_VISIBLE_ROWS)
        self._preset_manage_scroll = min(self._preset_manage_scroll, max_manage_scroll)

    def _refresh_buttons(self) -> None:
        self._buttons = buttons_for_state(
            self._state,
            placement_ready=PlacementEditorService.all_ships_placed(self._placements_by_type, _SHIP_ORDER),
            has_presets=bool(self._preset_rows),
        )
        if self._state is AppState.PRESET_MANAGE:
            self._buttons.extend(preset_row_buttons(self._visible_preset_manage_rows()))
        if self._state is AppState.NEW_GAME_SETUP:
            self._buttons.extend(
                new_game_setup_buttons(
                    rows=self._preset_rows,
                    scroll=self._new_game_preset_scroll,
                    visible_rows=_NEW_GAME_VISIBLE_PRESET_ROWS,
                    difficulty_open=self._new_game_difficulty_open,
                )
            )
        if self._prompt_state.prompt is not None:
            self._buttons.extend(prompt_buttons(self._prompt_state.prompt))

    def _visible_preset_manage_rows(self) -> list[PresetRowView]:
        start = self._preset_manage_scroll
        end = start + _PRESET_MANAGE_VISIBLE_ROWS
        return list(self._preset_rows[start:end])

    def _preset_manage_can_scroll_down(self) -> bool:
        return self._preset_manage_scroll + _PRESET_MANAGE_VISIBLE_ROWS < len(self._preset_rows)

    def _announce_state(self) -> None:
        logger.info("state=%s", self._state.name)
        if self._debug_ui:
            logger.debug("buttons=%s", [button.id for button in self._buttons])

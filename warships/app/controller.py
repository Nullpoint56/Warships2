"""Application controller for state transitions and game flow."""

from __future__ import annotations

from collections.abc import Callable
import logging
import random

from warships.ai.strategy import AIStrategy
from warships.app.flows.placement_math import bow_from_grab_index, grab_index_from_cell
from warships.app.services.battle import resolve_player_turn, start_game
from warships.app.services.placement_editor import PlacementEditorService
from warships.app.services.preset_flow import PresetFlowService
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState, PresetRowView, TextPromptView
from warships.core.fleet import random_fleet
from warships.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType, cells_for_placement
from warships.core.rules import GameSession
from warships.presets.service import PresetService
from warships.ui.board_view import BoardLayout
from warships.ui.layout_metrics import NEW_GAME_SETUP, PRESET_PANEL, PROMPT
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
_DIFFICULTIES = ["Easy", "Normal", "Hard"]
_NEW_GAME_VISIBLE_PRESET_ROWS = 5


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
        self._editing_preset_name: str | None = None
        self._new_game_difficulty_index = 1
        self._new_game_difficulty_open = False
        self._new_game_selected_preset: str | None = None
        self._new_game_preset_scroll = 0
        self._new_game_random_fleet: FleetPlacement | None = None
        self._new_game_preview: list[ShipPlacement] = []
        self._new_game_source_label: str | None = None

        self._prompt: TextPromptView | None = None
        self._prompt_buffer: str = ""
        self._prompt_mode: str | None = None
        self._prompt_target: str | None = None
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
            preset_rows=list(self._preset_rows),
            prompt=self._prompt,
            held_ship_type=self._held_ship_type,
            held_ship_orientation=self._held_orientation,
            held_grab_index=self._held_grab_index,
            hover_cell=self._hover_cell,
            hover_x=self._hover_x,
            hover_y=self._hover_y,
            new_game_difficulty=self._current_difficulty(),
            new_game_difficulty_open=self._new_game_difficulty_open,
            new_game_difficulty_options=list(_DIFFICULTIES),
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
        )

    def handle_button(self, event: ButtonPressed) -> bool:
        """Process button event. Returns whether UI changed."""
        button_id = event.button_id
        if self._prompt is not None:
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
        self._state = AppState.PRESET_MANAGE
        self._status = "Manage presets."
        self._refresh_preset_rows()
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_new_game(self) -> bool:
        self._state = AppState.NEW_GAME_SETUP
        self._enter_new_game_setup()
        self._status = "Configure game: difficulty and fleet selection."
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_create_preset(self) -> bool:
        self._state = AppState.PLACEMENT_EDIT
        self._status = "Drag a ship from panel, drop onto board. Press R while holding to rotate."
        self._reset_editor()
        self._editing_preset_name = None
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_back_main(self) -> bool:
        self._state = AppState.MAIN_MENU
        self._status = "Choose New Game, Manage Presets, or Quit."
        self._session = None
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_toggle_new_game_difficulty(self) -> bool:
        self._new_game_difficulty_open = not self._new_game_difficulty_open
        self._refresh_buttons()
        return True

    def _on_new_game_diff_option(self, diff: str) -> bool:
        if diff not in _DIFFICULTIES:
            return False
        self._new_game_difficulty_index = _DIFFICULTIES.index(diff)
        self._new_game_difficulty_open = False
        self._status = f"Difficulty: {self._current_difficulty()}."
        self._refresh_buttons()
        return True

    def _on_new_game_randomize(self) -> bool:
        self._new_game_random_fleet = random_fleet(self._rng)
        self._new_game_selected_preset = None
        self._new_game_preview = list(self._new_game_random_fleet.ships)
        self._new_game_source_label = "Random Fleet"
        self._status = "Generated random fleet for this game."
        return True

    def _on_quit(self) -> bool:
        self._is_closing = True
        return True

    def _on_play_again(self) -> bool:
        self._state = AppState.NEW_GAME_SETUP
        self._enter_new_game_setup()
        self._status = "Configure game: difficulty and fleet selection."
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_back_to_presets(self) -> bool:
        self._state = AppState.PRESET_MANAGE
        self._status = "Manage presets."
        self._refresh_preset_rows()
        self._refresh_buttons()
        self._announce_state()
        return True

    def _on_save_preset(self) -> bool:
        if not PlacementEditorService.all_ships_placed(self._placements_by_type, _SHIP_ORDER):
            self._status = "Place all ships before saving."
            return True
        default_name = self._editing_preset_name or "new_preset"
        self._open_prompt("Save Preset", default_name, mode="save")
        self._refresh_buttons()
        return True

    def _on_preset_rename(self, name: str) -> bool:
        self._open_prompt("Rename Preset", name, mode="rename", target=name)
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
        if self._held_ship_type is None or self._held_orientation is None:
            return False
        target = PlacementEditorService.to_board_cell(_BOARD_LAYOUT, event.x, event.y)
        if target is None:
            self._restore_held_ship()
            self._refresh_buttons()
            return True
        bow = bow_from_grab_index(target, self._held_orientation, self._held_grab_index)
        candidate = ShipPlacement(self._held_ship_type, bow, self._held_orientation)
        if PlacementEditorService.can_place(self._placements_by_type, candidate):
            self._placements_by_type[self._held_ship_type] = candidate
            self._status = f"Placed {self._held_ship_type.value}."
        else:
            self._restore_held_ship()
            self._status = "Invalid drop position."
        self._held_ship_type = None
        self._held_orientation = None
        self._held_previous = None
        self._held_grab_index = 0
        self._refresh_buttons()
        return True

    def handle_key_pressed(self, event: KeyPressed) -> bool:
        """Handle key-down events for prompt and placement rotation."""
        key = event.key.lower()
        if self._prompt is not None:
            if key in {"backspace"}:
                self._prompt_buffer = self._prompt_buffer[:-1]
                self._sync_prompt()
                return True
            if key in {"enter"}:
                return self._confirm_prompt()
            if key in {"escape"}:
                self._close_prompt()
                self._refresh_buttons()
                return True
            return False

        if self._state is AppState.PLACEMENT_EDIT and self._held_ship_type is not None and key == "r":
            self._held_orientation = (
                Orientation.VERTICAL
                if self._held_orientation is Orientation.HORIZONTAL
                else Orientation.HORIZONTAL
            )
            self._status = f"Holding {self._held_ship_type.value} ({self._held_orientation.value})."
            return True
        if self._state is AppState.PLACEMENT_EDIT and self._held_ship_type is not None and key == "d":
            deleted = self._held_ship_type
            self._held_ship_type = None
            self._held_orientation = None
            self._held_previous = None
            self._held_grab_index = 0
            self._status = f"Deleted {deleted.value} from hand."
            self._refresh_buttons()
            return True
        return False

    def handle_char_typed(self, event: CharTyped) -> bool:
        """Handle text input for prompt."""
        if self._prompt is None:
            return False
        ch = event.char
        if len(ch) != 1 or not ch.isprintable():
            return False
        if len(self._prompt_buffer) >= 32:
            return False
        self._prompt_buffer += ch
        self._sync_prompt()
        return True

    def handle_wheel(self, x: float, y: float, dy: float) -> bool:
        """Handle mouse wheel interactions."""
        if self._state is not AppState.NEW_GAME_SETUP:
            return False
        list_rect = NEW_GAME_SETUP.preset_list_rect()
        if not list_rect.contains(x, y):
            return False
        return self.scroll_new_game_presets(dy)

    def scroll_new_game_presets(self, dy: float) -> bool:
        """Scroll the new-game preset list by wheel delta semantics."""
        if self._state is not AppState.NEW_GAME_SETUP:
            return False
        if dy < 0 and self._new_game_preset_scroll > 0:
            self._new_game_preset_scroll -= 1
            self._refresh_buttons()
            return True
        if dy > 0 and PresetFlowService.can_scroll_down(
            self._preset_rows, self._new_game_preset_scroll, _NEW_GAME_VISIBLE_PRESET_ROWS
        ):
            self._new_game_preset_scroll += 1
            self._refresh_buttons()
            return True
        return False

    def submit_prompt_text(self, text: str) -> bool:
        """Set current prompt text and confirm it."""
        if self._prompt is None:
            return False
        self._prompt_buffer = text[:32]
        self._sync_prompt()
        return self._confirm_prompt()

    def cancel_prompt(self) -> bool:
        """Cancel currently open prompt."""
        if self._prompt is None:
            return False
        self._close_prompt()
        self._refresh_buttons()
        return True

    def handle_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Pick ship from board or palette."""
        if self._state is not AppState.PLACEMENT_EDIT or self._prompt is not None:
            return False
        if button == 2:
            if self._held_ship_type is not None:
                self._restore_held_ship()
                self._status = "Returned held ship."
                self._refresh_buttons()
                return True
            board_cell = PlacementEditorService.to_board_cell(_BOARD_LAYOUT, x, y)
            if board_cell is None:
                return False
            for ship_type, placement in self._placements_by_type.items():
                if placement and board_cell in cells_for_placement(placement):
                    self._placements_by_type[ship_type] = None
                    self._status = f"Removed {ship_type.value}."
                    self._refresh_buttons()
                    return True
            return False
        if button != 1:
            return False

        board_cell = PlacementEditorService.to_board_cell(_BOARD_LAYOUT, x, y)
        self._hover_x = x
        self._hover_y = y
        if board_cell is not None:
            for ship_type, placement in self._placements_by_type.items():
                if placement and board_cell in cells_for_placement(placement):
                    self._held_ship_type = ship_type
                    self._held_orientation = placement.orientation
                    self._held_previous = placement
                    self._held_grab_index = grab_index_from_cell(placement, board_cell)
                    self._placements_by_type[ship_type] = None
                    self._status = f"Holding {ship_type.value}. Press R to rotate."
                    self._refresh_buttons()
                    return True

        palette_ship = PlacementEditorService.palette_ship_at_point(_SHIP_ORDER, x, y)
        if palette_ship is not None:
            if self._placements_by_type.get(palette_ship) is not None:
                self._status = f"{palette_ship.value} is already placed."
                return True
            self._held_ship_type = palette_ship
            self._held_orientation = Orientation.HORIZONTAL
            self._held_previous = None
            self._held_grab_index = max(0, palette_ship.size // 2)
            self._status = f"Holding {palette_ship.value}. Press R to rotate."
            return True
        return False

    def _handle_prompt_button(self, button_id: str) -> bool:
        if button_id == "prompt_cancel":
            self._close_prompt()
            self._refresh_buttons()
            return True
        if button_id in {"prompt_confirm_save", "prompt_confirm_rename", "prompt_confirm_overwrite"}:
            return self._confirm_prompt()
        return False

    def _confirm_prompt(self) -> bool:
        value = self._prompt_buffer.strip()
        if not value:
            self._status = "Name cannot be empty."
            return True
        if self._prompt_mode == "save":
            fleet = FleetPlacement(ships=PlacementEditorService.placements_list(self._placements_by_type))
            exists = any(row.name == value for row in self._preset_rows)
            if exists and value != (self._editing_preset_name or ""):
                self._pending_save_name = value
                self._open_prompt("Preset exists. Overwrite?", value, mode="overwrite")
                self._refresh_buttons()
                return True
            try:
                self._preset_service.save_preset(value, fleet)
            except ValueError as exc:
                self._status = f"Save failed: {exc}"
                return True
            self._editing_preset_name = value
            self._status = f"Saved preset '{value}'."
            self._close_prompt()
            self._state = AppState.PRESET_MANAGE
            self._refresh_preset_rows()
            self._refresh_buttons()
            self._announce_state()
            return True
        if self._prompt_mode == "overwrite":
            target = self._pending_save_name or value
            try:
                self._preset_service.save_preset(
                    target,
                    FleetPlacement(ships=PlacementEditorService.placements_list(self._placements_by_type)),
                )
            except ValueError as exc:
                self._status = f"Save failed: {exc}"
                return True
            self._editing_preset_name = target
            self._status = f"Overwrote preset '{target}'."
            self._pending_save_name = None
            self._close_prompt()
            self._state = AppState.PRESET_MANAGE
            self._refresh_preset_rows()
            self._refresh_buttons()
            self._announce_state()
            return True
        if self._prompt_mode == "rename" and self._prompt_target:
            try:
                self._preset_service.rename_preset(self._prompt_target, value)
            except (ValueError, FileNotFoundError) as exc:
                self._status = f"Rename failed: {exc}"
                return True
            self._status = f"Renamed '{self._prompt_target}' to '{value}'."
            self._close_prompt()
            self._refresh_preset_rows()
            self._refresh_buttons()
            return True
        return False

    def _edit_preset(self, name: str) -> bool:
        fleet = self._preset_service.load_preset(name)
        self._state = AppState.PLACEMENT_EDIT
        self._reset_editor()
        for placement in fleet.ships:
            self._placements_by_type[placement.ship_type] = placement
        self._editing_preset_name = name
        self._status = f"Editing preset '{name}'. Drag ships to adjust."
        self._refresh_buttons()
        self._announce_state()
        return True

    def _open_prompt(self, title: str, initial_value: str, mode: str, target: str | None = None) -> None:
        self._prompt_mode = mode
        self._prompt_target = target
        self._prompt_buffer = initial_value
        self._prompt = PresetFlowService.open_prompt(title, self._prompt_buffer, mode)

    def _close_prompt(self) -> None:
        self._prompt = None
        self._prompt_buffer = ""
        self._prompt_mode = None
        self._prompt_target = None

    def _sync_prompt(self) -> None:
        if self._prompt is None:
            return
        self._prompt = PresetFlowService.sync_prompt(self._prompt, self._prompt_buffer)

    def _reset_editor(self) -> None:
        self._placements_by_type = PlacementEditorService.reset(_SHIP_ORDER)
        self._held_ship_type = None
        self._held_orientation = None
        self._held_previous = None
        self._held_grab_index = 0
        self._hover_cell = None
        self._hover_x = None
        self._hover_y = None

    def _restore_held_ship(self) -> None:
        if self._held_ship_type and self._held_previous:
            self._placements_by_type[self._held_ship_type] = self._held_previous
        self._held_ship_type = None
        self._held_orientation = None
        self._held_previous = None
        self._held_grab_index = 0

    def _randomize_editor(self) -> bool:
        self._reset_editor()
        for placement in random_fleet(self._rng).ships:
            self._placements_by_type[placement.ship_type] = placement
        self._status = "Placement randomized."
        self._refresh_buttons()
        return True

    def _current_difficulty(self) -> str:
        return _DIFFICULTIES[self._new_game_difficulty_index]

    def _enter_new_game_setup(self) -> None:
        self._refresh_preset_rows()
        self._new_game_difficulty_open = False
        self._new_game_preset_scroll = 0
        self._new_game_random_fleet = None
        if self._preset_rows:
            self._select_new_game_preset(self._preset_rows[0].name)
        else:
            self._new_game_selected_preset = None
            self._new_game_preview = []
            self._new_game_source_label = None

    def _select_new_game_preset(self, name: str) -> bool:
        result = PresetFlowService.select_new_game_preset(self._preset_service, name)
        self._new_game_selected_preset = result.selected_preset
        self._new_game_random_fleet = result.random_fleet
        self._new_game_preview = result.preview
        self._new_game_source_label = result.source_label
        self._status = result.status
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
        self._state = AppState.BATTLE
        self._status = result.status
        self._refresh_buttons()
        self._announce_state()
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

    def _refresh_buttons(self) -> None:
        self._buttons = buttons_for_state(
            self._state,
            placement_ready=PlacementEditorService.all_ships_placed(self._placements_by_type, _SHIP_ORDER),
            has_presets=bool(self._preset_rows),
        )
        if self._state is AppState.PRESET_MANAGE:
            self._buttons.extend(_preset_row_buttons(self._preset_rows))
        if self._state is AppState.NEW_GAME_SETUP:
            self._buttons.extend(_new_game_setup_buttons(self))
        if self._prompt is not None:
            self._buttons.extend(_prompt_buttons(self._prompt))

    def _announce_state(self) -> None:
        logger.info("state=%s", self._state.name)
        if self._debug_ui:
            logger.debug("buttons=%s", [button.id for button in self._buttons])


def _prompt_buttons(prompt: TextPromptView) -> list[Button]:
    confirm = PROMPT.confirm_button_rect()
    cancel = PROMPT.cancel_button_rect()
    return [
        Button(prompt.confirm_button_id, confirm.x, confirm.y, confirm.w, confirm.h),
        Button(prompt.cancel_button_id, cancel.x, cancel.y, cancel.w, cancel.h),
    ]


def _preset_row_buttons(rows: list[PresetRowView]) -> list[Button]:
    buttons: list[Button] = []
    for idx, row in enumerate(rows):
        edit_rect, rename_rect, delete_rect = PRESET_PANEL.action_button_rects(idx)
        buttons.append(Button(f"preset_edit:{row.name}", edit_rect.x, edit_rect.y, edit_rect.w, edit_rect.h))
        buttons.append(Button(f"preset_rename:{row.name}", rename_rect.x, rename_rect.y, rename_rect.w, rename_rect.h))
        buttons.append(Button(f"preset_delete:{row.name}", delete_rect.x, delete_rect.y, delete_rect.w, delete_rect.h))
    return buttons


def _new_game_setup_buttons(controller: GameController) -> list[Button]:
    buttons: list[Button] = []
    difficulty = NEW_GAME_SETUP.difficulty_rect()
    buttons.append(Button("new_game_toggle_difficulty", difficulty.x, difficulty.y, difficulty.w, difficulty.h))
    if controller._new_game_difficulty_open:
        for idx, name in enumerate(_DIFFICULTIES):
            rect = NEW_GAME_SETUP.difficulty_option_rect(idx)
            buttons.append(Button(f"new_game_diff_option:{name}", rect.x, rect.y, rect.w, rect.h))

    for idx, name in enumerate(
        PresetFlowService.visible_new_game_preset_names(
            controller._preset_rows,
            controller._new_game_preset_scroll,
            _NEW_GAME_VISIBLE_PRESET_ROWS,
        )
    ):
        row_rect = NEW_GAME_SETUP.preset_row_rect(idx)
        buttons.append(Button(f"new_game_select_preset:{name}", row_rect.x, row_rect.y, row_rect.w, row_rect.h))
    random_rect = NEW_GAME_SETUP.random_button_rect()
    buttons.append(Button("new_game_randomize", random_rect.x, random_rect.y, random_rect.w, random_rect.h))
    return buttons

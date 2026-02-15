"""Application controller for state transitions and game flow."""

from __future__ import annotations

import logging
import random

from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState, PresetRowView, TextPromptView
from warships.core.board import BoardState
from warships.core.fleet import validate_fleet
from warships.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType
from warships.presets.service import PresetService
from warships.ui.board_view import BoardLayout
from warships.ui.layout_metrics import PLACEMENT_PANEL, PRESET_PANEL, PROMPT
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


class GameController:
    """Handles app events and owns editor state."""

    def __init__(self, preset_service: PresetService, rng: random.Random, debug_ui: bool = False) -> None:
        self._preset_service = preset_service
        self._rng = rng
        self._debug_ui = debug_ui

        self._state = AppState.MAIN_MENU
        self._status = "Open preset manager."
        self._is_closing = False

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

        self._prompt: TextPromptView | None = None
        self._prompt_buffer: str = ""
        self._prompt_mode: str | None = None
        self._prompt_target: str | None = None
        self._pending_save_name: str | None = None

        self._buttons: list[Button] = []
        self._refresh_preset_rows()
        self._refresh_buttons()
        self._announce_state()

    def ui_state(self) -> AppUIState:
        """Return current view-ready state."""
        return AppUIState(
            state=self._state,
            status=self._status,
            buttons=self._buttons,
            placements=self._placements_list(),
            placement_orientation=self._held_orientation or Orientation.HORIZONTAL,
            session=None,
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
        )

    def handle_button(self, event: ButtonPressed) -> bool:
        """Process button event. Returns whether UI changed."""
        button_id = event.button_id
        if self._prompt is not None:
            return self._handle_prompt_button(button_id)

        if button_id == "manage_presets":
            self._state = AppState.PRESET_MANAGE
            self._status = "Manage presets."
            self._refresh_preset_rows()
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "create_preset":
            self._state = AppState.PLACEMENT_EDIT
            self._status = "Drag a ship from panel, drop onto board. Press R while holding to rotate."
            self._reset_editor()
            self._editing_preset_name = None
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "back_main":
            self._state = AppState.MAIN_MENU
            self._status = "Open preset manager."
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "quit":
            self._is_closing = True
            return True
        if button_id == "back_to_presets":
            self._state = AppState.PRESET_MANAGE
            self._status = "Manage presets."
            self._refresh_preset_rows()
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "save_preset":
            if not self._all_ships_placed():
                self._status = "Place all ships before saving."
                return True
            default_name = self._editing_preset_name or "new_preset"
            self._open_prompt("Save Preset", default_name, mode="save")
            self._refresh_buttons()
            return True
        if button_id == "randomize":
            return self._randomize_editor()

        if button_id.startswith("preset_edit:"):
            name = button_id.split(":", 1)[1]
            return self._edit_preset(name)
        if button_id.startswith("preset_rename:"):
            name = button_id.split(":", 1)[1]
            self._open_prompt("Rename Preset", name, mode="rename", target=name)
            self._refresh_buttons()
            return True
        if button_id.startswith("preset_delete:"):
            name = button_id.split(":", 1)[1]
            self._preset_service.delete_preset(name)
            self._status = f"Deleted preset '{name}'."
            self._refresh_preset_rows()
            self._refresh_buttons()
            return True
        return False

    def handle_board_click(self, event: BoardCellPressed) -> bool:
        """Compatibility no-op for current pointer-driven editor."""
        return False

    def handle_pointer_move(self, event: PointerMoved) -> bool:
        """Update hover cell while dragging in editor."""
        if self._state is not AppState.PLACEMENT_EDIT:
            return False
        self._hover_x = event.x
        self._hover_y = event.y
        self._hover_cell = _to_board_cell(event.x, event.y)
        return self._held_ship_type is not None

    def handle_pointer_release(self, event: PointerReleased) -> bool:
        """Drop held ship on pointer release."""
        if self._state is not AppState.PLACEMENT_EDIT:
            return False
        if event.button != 1:
            return False
        if self._held_ship_type is None or self._held_orientation is None:
            return False
        target = _to_board_cell(event.x, event.y)
        if target is None:
            self._restore_held_ship()
            return True
        bow = _bow_from_grab_index(target, self._held_orientation, self._held_grab_index)
        candidate = ShipPlacement(self._held_ship_type, bow, self._held_orientation)
        if self._can_place(candidate):
            self._placements_by_type[self._held_ship_type] = candidate
            self._status = f"Placed {self._held_ship_type.value}."
        else:
            self._restore_held_ship()
            self._status = "Invalid drop position."
        self._held_ship_type = None
        self._held_orientation = None
        self._held_previous = None
        self._held_grab_index = 0
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

    def handle_pointer_down(self, x: float, y: float, button: int) -> bool:
        """Pick ship from board or palette."""
        if self._state is not AppState.PLACEMENT_EDIT or self._prompt is not None:
            return False
        if button == 2:
            if self._held_ship_type is not None:
                self._restore_held_ship()
                self._status = "Returned held ship."
                return True
            board_cell = _to_board_cell(x, y)
            if board_cell is None:
                return False
            for ship_type, placement in self._placements_by_type.items():
                if placement and board_cell in _cells_for_ship(placement):
                    self._placements_by_type[ship_type] = None
                    self._status = f"Removed {ship_type.value}."
                    self._refresh_buttons()
                    return True
            return False
        if button != 1:
            return False

        board_cell = _to_board_cell(x, y)
        self._hover_x = x
        self._hover_y = y
        if board_cell is not None:
            for ship_type, placement in self._placements_by_type.items():
                if placement and board_cell in _cells_for_ship(placement):
                    self._held_ship_type = ship_type
                    self._held_orientation = placement.orientation
                    self._held_previous = placement
                    self._held_grab_index = _grab_index_from_cell(placement, board_cell)
                    self._placements_by_type[ship_type] = None
                    self._status = f"Holding {ship_type.value}. Press R to rotate."
                    return True

        palette_ship = _palette_ship_at_point(x, y)
        if palette_ship is not None:
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
            fleet = FleetPlacement(ships=self._placements_list())
            exists = any(row.name == value for row in self._preset_rows)
            if exists and value != (self._editing_preset_name or ""):
                self._pending_save_name = value
                self._open_prompt("Preset exists. Overwrite?", value, mode="overwrite")
                self._refresh_buttons()
                return True
            try:
                self._preset_service.save_preset(value, fleet)
            except Exception as exc:
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
                self._preset_service.save_preset(target, FleetPlacement(ships=self._placements_list()))
            except Exception as exc:
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
            except Exception as exc:
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
        if mode == "save":
            confirm = "prompt_confirm_save"
        elif mode == "rename":
            confirm = "prompt_confirm_rename"
        else:
            confirm = "prompt_confirm_overwrite"
        self._prompt = TextPromptView(
            title=title,
            value=self._prompt_buffer,
            confirm_button_id=confirm,
            cancel_button_id="prompt_cancel",
        )

    def _close_prompt(self) -> None:
        self._prompt = None
        self._prompt_buffer = ""
        self._prompt_mode = None
        self._prompt_target = None

    def _sync_prompt(self) -> None:
        if self._prompt is None:
            return
        self._prompt = TextPromptView(
            title=self._prompt.title,
            value=self._prompt_buffer,
            confirm_button_id=self._prompt.confirm_button_id,
            cancel_button_id=self._prompt.cancel_button_id,
        )

    def _reset_editor(self) -> None:
        self._placements_by_type = {ship_type: None for ship_type in _SHIP_ORDER}
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

    def _placements_list(self) -> list[ShipPlacement]:
        return [placement for placement in self._placements_by_type.values() if placement is not None]

    def _all_ships_placed(self) -> bool:
        return all(self._placements_by_type[ship_type] is not None for ship_type in _SHIP_ORDER)

    def _can_place(self, candidate: ShipPlacement) -> bool:
        board = BoardState()
        temp: list[ShipPlacement] = [p for p in self._placements_by_type.values() if p is not None]
        temp.append(candidate)
        seen: set[ShipType] = set()
        for idx, placement in enumerate(temp, start=1):
            if placement.ship_type in seen:
                return False
            seen.add(placement.ship_type)
            if not board.can_place(placement):
                return False
            board.place_ship(idx, placement)
        return True

    def _randomize_editor(self) -> bool:
        from warships.core.fleet import random_fleet

        fleet = random_fleet(self._rng)
        self._reset_editor()
        for placement in fleet.ships:
            self._placements_by_type[placement.ship_type] = placement
        self._status = "Placement randomized."
        self._refresh_buttons()
        return True

    def _refresh_preset_rows(self) -> None:
        rows: list[PresetRowView] = []
        for name in self._preset_service.list_presets():
            try:
                fleet = self._preset_service.load_preset(name)
            except Exception:
                continue
            rows.append(PresetRowView(name=name, placements=list(fleet.ships)))
        self._preset_rows = rows

    def _refresh_buttons(self) -> None:
        self._buttons = buttons_for_state(
            self._state,
            placement_ready=self._all_ships_placed(),
            has_presets=bool(self._preset_rows),
        )
        if self._state is AppState.PRESET_MANAGE:
            self._buttons.extend(_preset_row_buttons(self._preset_rows))
        if self._prompt is not None:
            self._buttons.extend(_prompt_buttons(self._prompt))

    def _announce_state(self) -> None:
        logger.info("state=%s", self._state.name)
        if self._debug_ui:
            logger.debug("buttons=%s", [button.id for button in self._buttons])


def _validate_partial_fleet(fleet: FleetPlacement) -> tuple[bool, str]:
    valid, reason = validate_fleet(fleet)
    if valid:
        return True, ""
    if "exactly five ships" in reason:
        board = BoardState()
        seen: set[ShipType] = set()
        for idx, placement in enumerate(fleet.ships, start=1):
            if placement.ship_type in seen:
                return False, "Duplicate ship type."
            seen.add(placement.ship_type)
            if not board.can_place(placement):
                return False, "Invalid placement."
            board.place_ship(idx, placement)
        return True, ""
    return False, reason


def _to_board_cell(x: float, y: float) -> Coord | None:
    return _BOARD_LAYOUT.screen_to_cell(is_ai=False, px=x, py=y)


def _palette_ship_at_point(x: float, y: float) -> ShipType | None:
    panel = PLACEMENT_PANEL.panel_rect()
    if not panel.contains(x, y):
        return None
    for index, ship_type in enumerate(_SHIP_ORDER):
        row = PLACEMENT_PANEL.row_rect(index)
        if row.contains(x, y):
            return ship_type
    return None


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


def _cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    cells: list[Coord] = []
    for offset in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            cells.append(Coord(row=placement.bow.row, col=placement.bow.col + offset))
        else:
            cells.append(Coord(row=placement.bow.row + offset, col=placement.bow.col))
    return cells


def _grab_index_from_cell(placement: ShipPlacement, cell: Coord) -> int:
    if placement.orientation is Orientation.HORIZONTAL:
        return max(0, cell.col - placement.bow.col)
    return max(0, cell.row - placement.bow.row)


def _bow_from_grab_index(cell: Coord, orientation: Orientation, grab_index: int) -> Coord:
    if orientation is Orientation.HORIZONTAL:
        return Coord(row=cell.row, col=cell.col - grab_index)
    return Coord(row=cell.row - grab_index, col=cell.col)

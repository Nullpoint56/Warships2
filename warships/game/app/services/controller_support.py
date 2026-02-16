"""Controller support collaborator for non-domain state/view orchestration."""

from __future__ import annotations

import logging

from warships.game.app.ports.runtime_services import can_scroll_list_down, visible_slice
from warships.game.app.controller_state import ControllerState
from warships.game.app.services.placement_editor import PlacementEditorService
from warships.game.app.services.ui_buttons import compose_buttons
from warships.game.core.models import FleetPlacement, ShipPlacement, ShipType


class ControllerSupport:
    """Encapsulate controller-local utility operations and view projections."""

    def __init__(
        self,
        *,
        state: ControllerState,
        ship_order: list[ShipType],
        new_game_visible_rows: int,
        preset_manage_visible_rows: int,
        logger: logging.Logger,
        debug_ui: bool,
    ) -> None:
        self._state = state
        self._ship_order = ship_order
        self._new_game_visible_rows = new_game_visible_rows
        self._preset_manage_visible_rows = preset_manage_visible_rows
        self._logger = logger
        self._debug_ui = debug_ui

    def reset_editor(self) -> None:
        self._state.placements_by_type = PlacementEditorService.reset(self._ship_order)
        self._state.held_ship_type = None
        self._state.held_orientation = None
        self._state.held_previous = None
        self._state.held_grab_index = 0
        self._state.hover_cell = None
        self._state.hover_x = None
        self._state.hover_y = None

    def apply_loaded_placements(self, placements: list[ShipPlacement]) -> None:
        for placement in placements:
            self._state.placements_by_type[placement.ship_type] = placement

    def apply_new_game_selection(
        self,
        *,
        selected_preset: str | None,
        random_fleet: FleetPlacement | None,
        preview: list[ShipPlacement],
        source_label: str | None,
    ) -> None:
        self._state.new_game_selected_preset = selected_preset
        self._state.new_game_random_fleet = random_fleet
        self._state.new_game_preview = preview
        self._state.new_game_source_label = source_label

    def set_status(self, status: str) -> None:
        self._state.status = status

    def refresh_buttons(self) -> None:
        self._state.buttons = compose_buttons(
            state=self._state.app_state,
            placement_ready=PlacementEditorService.all_ships_placed(self._state.placements_by_type, self._ship_order),
            has_presets=bool(self._state.preset_rows),
            visible_preset_manage_rows=visible_slice(
                self._state.preset_rows,
                self._state.preset_manage_scroll,
                self._preset_manage_visible_rows,
            ),
            preset_rows=self._state.preset_rows,
            new_game_preset_scroll=self._state.new_game_preset_scroll,
            new_game_visible_rows=self._new_game_visible_rows,
            new_game_difficulty_open=self._state.new_game_difficulty_open,
            prompt=self._state.prompt_state.prompt,
        )

    def preset_manage_can_scroll_down(self) -> bool:
        return can_scroll_list_down(
            scroll=self._state.preset_manage_scroll,
            visible_count=self._preset_manage_visible_rows,
            total_count=len(self._state.preset_rows),
        )

    def announce_state(self) -> None:
        self._logger.info("state=%s", self._state.app_state.name)
        if self._debug_ui:
            self._logger.debug("buttons=%s", [button.id for button in self._state.buttons])

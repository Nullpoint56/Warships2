"""UI state projection helpers for controller snapshots."""

from __future__ import annotations

from warships.game.app.services.new_game_flow import DIFFICULTIES
from warships.game.app.services.placement_editor import PlacementEditorService
from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState, PresetRowView
from warships.game.core.models import Coord, Orientation, ShipPlacement, ShipType
from warships.game.core.rules import GameSession
from warships.game.ui.overlays import Button


def visible_rows(rows: list[PresetRowView], scroll: int, visible_count: int) -> list[PresetRowView]:
    """Slice visible rows for list-like UIs."""
    start = scroll
    end = start + visible_count
    return list(rows[start:end])


def can_scroll_down(scroll: int, visible_count: int, total_count: int) -> bool:
    """Return whether another row below is available."""
    return scroll + visible_count < total_count


def build_ui_state(
    *,
    state: AppState,
    status: str,
    buttons: list[Button],
    placements_by_type: dict[ShipType, ShipPlacement | None],
    held_orientation: Orientation | None,
    session: GameSession | None,
    ship_order: list[ShipType],
    is_closing: bool,
    preset_rows: list[PresetRowView],
    preset_manage_scroll: int,
    preset_manage_visible_rows: int,
    prompt,
    held_ship_type: ShipType | None,
    held_ship_orientation: Orientation | None,
    held_grab_index: int,
    hover_cell: Coord | None,
    hover_x: float | None,
    hover_y: float | None,
    new_game_difficulty: str | None,
    new_game_difficulty_open: bool,
    new_game_preset_scroll: int,
    new_game_visible_rows: int,
    new_game_selected_preset: str | None,
    new_game_source: str | None,
    new_game_preview: list[ShipPlacement],
) -> AppUIState:
    """Build AppUIState from controller snapshot fields."""
    placements = PlacementEditorService.placements_list(placements_by_type)
    return AppUIState(
        state=state,
        status=status,
        buttons=buttons,
        placements=placements,
        placement_orientation=held_orientation or Orientation.HORIZONTAL,
        session=session,
        ship_order=ship_order,
        is_closing=is_closing,
        preset_rows=visible_rows(preset_rows, preset_manage_scroll, preset_manage_visible_rows),
        prompt=prompt,
        held_ship_type=held_ship_type,
        held_ship_orientation=held_ship_orientation,
        held_grab_index=held_grab_index,
        hover_cell=hover_cell,
        hover_x=hover_x,
        hover_y=hover_y,
        new_game_difficulty=new_game_difficulty,
        new_game_difficulty_open=new_game_difficulty_open,
        new_game_difficulty_options=list(DIFFICULTIES),
        new_game_visible_presets=PresetFlowService.visible_new_game_preset_names(
            preset_rows, new_game_preset_scroll, new_game_visible_rows
        ),
        new_game_selected_preset=new_game_selected_preset,
        new_game_can_scroll_up=new_game_preset_scroll > 0,
        new_game_can_scroll_down=PresetFlowService.can_scroll_down(
            preset_rows, new_game_preset_scroll, new_game_visible_rows
        ),
        new_game_source=new_game_source,
        new_game_preview=list(new_game_preview),
        preset_manage_can_scroll_up=preset_manage_scroll > 0,
        preset_manage_can_scroll_down=can_scroll_down(
            scroll=preset_manage_scroll,
            visible_count=preset_manage_visible_rows,
            total_count=len(preset_rows),
        ),
    )

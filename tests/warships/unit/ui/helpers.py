from __future__ import annotations

from engine.ui_runtime.widgets import Button
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState, PresetRowView
from warships.game.core.models import Orientation, ShipPlacement, ShipType


class FakeRenderer:
    def __init__(self) -> None:
        self.rects: list[tuple] = []
        self.texts: list[tuple] = []
        self.grids: list[tuple] = []

    def add_rect(self, *args, **kwargs) -> None:
        self.rects.append((args, kwargs))

    def add_text(self, *args, **kwargs) -> None:
        self.texts.append((args, kwargs))

    def add_grid(self, *args, **kwargs) -> None:
        self.grids.append((args, kwargs))


def make_ui_state(
    *,
    state: AppState = AppState.MAIN_MENU,
    preset_rows: list[PresetRowView] | None = None,
    new_game_visible_presets: list[str] | None = None,
    new_game_preview: list[ShipPlacement] | None = None,
    new_game_difficulty_open: bool = False,
) -> AppUIState:
    return AppUIState(
        state=state,
        status="status",
        buttons=[Button("new_game", 0, 0, 10, 10)],
        placements=[],
        placement_orientation=Orientation.HORIZONTAL,
        session=None,
        ship_order=[
            ShipType.CARRIER,
            ShipType.BATTLESHIP,
            ShipType.CRUISER,
            ShipType.SUBMARINE,
            ShipType.DESTROYER,
        ],
        is_closing=False,
        preset_rows=preset_rows or [],
        prompt=None,
        held_ship_type=None,
        held_ship_orientation=None,
        held_grab_index=0,
        hover_cell=None,
        hover_x=None,
        hover_y=None,
        held_preview_valid=True,
        held_preview_reason=None,
        placement_popup_message=None,
        new_game_difficulty="Normal",
        new_game_difficulty_open=new_game_difficulty_open,
        new_game_difficulty_options=["Easy", "Normal", "Hard"],
        new_game_visible_presets=new_game_visible_presets or [],
        new_game_selected_preset=(new_game_visible_presets or [None])[0]
        if new_game_visible_presets
        else None,
        new_game_can_scroll_up=False,
        new_game_can_scroll_down=False,
        new_game_source=None,
        new_game_preview=new_game_preview or [],
        preset_manage_can_scroll_up=False,
        preset_manage_can_scroll_down=False,
    )

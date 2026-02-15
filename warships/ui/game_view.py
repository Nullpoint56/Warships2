"""Retained-mode game rendering for Warships."""

from __future__ import annotations

import logging

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.board import BoardState
from warships.core.models import Coord, Orientation, ShipPlacement, ShipType, cells_for_placement
from warships.core.rules import GameSession
from warships.ui.board_view import BoardLayout
from warships.ui.framework.widgets import build_modal_text_input_widget, render_modal_text_input_widget
from warships.ui.layout_metrics import NEW_GAME_SETUP, PLACEMENT_PANEL, PRESET_PANEL, root_rect, status_rect
from warships.ui.overlays import Button, button_label
from warships.ui.render2d import Render2D

logger = logging.getLogger(__name__)


class GameView:
    """Draws game state using retained keyed scene nodes."""

    def __init__(self, renderer: Render2D, layout: BoardLayout) -> None:
        self._renderer = renderer
        self._layout = layout
        self._static_initialized = False

    def render(
        self,
        ui: AppUIState,
        debug_ui: bool,
        debug_labels_state: list[str],
    ) -> list[str]:
        """Draw current app state and return latest button labels for debug."""
        self._renderer.begin_frame()
        self._renderer.add_rect(
            "bg",
            root_rect().x,
            root_rect().y,
            root_rect().w,
            root_rect().h,
            "#0b132b",
            z=0.0,
        )

        labels = self._draw_buttons(ui.buttons)
        if ui.state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            self._draw_player_board(
                ui.placements,
                ui.session,
                ui.held_ship_type,
                ui.held_ship_orientation,
                ui.held_grab_index,
                ui.hover_cell,
                ui.hover_x,
                ui.hover_y,
            )
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            self._draw_ai_board(ui.state, ui.session)
        if ui.state is AppState.PLACEMENT_EDIT:
            self._draw_placement_panel(ui.placements, ui.ship_order)
        if ui.state is AppState.PRESET_MANAGE:
            self._draw_preset_manage(ui)
        if ui.state is AppState.NEW_GAME_SETUP:
            self._draw_new_game_setup(ui)
        prompt_widget = build_modal_text_input_widget(ui)
        if prompt_widget is not None:
            render_modal_text_input_widget(self._renderer, prompt_widget)

        self._draw_status_bar(ui.state, ui.status, ui.placement_orientation, ui.placements, ui.ship_order)
        self._renderer.set_title(f"Warships V1 | {ui.status}")

        if debug_ui and labels != debug_labels_state:
            logger.debug("ui_button_labels labels=%s", labels)
        self._renderer.end_frame()
        return labels

    def _draw_buttons(self, buttons: list[Button]) -> list[str]:
        labels: list[str] = []
        for button in buttons:
            if _is_new_game_custom_button(button.id):
                continue
            color = "#1f6feb" if button.enabled else "#384151"
            z = 10.4 if button.id.startswith("prompt_") else 1.0
            self._renderer.add_rect(
                f"button:bg:{button.id}",
                button.x,
                button.y,
                button.w,
                button.h,
                color,
                z=z,
            )
            label = button_label(button.id)
            labels.append(label)
            self._renderer.add_text(
                key=f"button:text:{button.id}",
                text=label,
                x=button.x + button.w / 2.0,
                y=button.y + button.h / 2.0,
                font_size=17.0,
                color="#e5e7eb",
                anchor="middle-center",
                z=10.5 if button.id.startswith("prompt_") else 3.0,
            )
        return labels

    def _draw_status_bar(
        self,
        state: AppState,
        status: str,
        placement_orientation: Orientation,
        placements: list[ShipPlacement],
        ship_order: list[ShipType],
    ) -> None:
        if state is AppState.MAIN_MENU:
            return
        status_box = status_rect()
        self._renderer.add_rect("status:bg", status_box.x, status_box.y, status_box.w, status_box.h, "#172554", z=1.0)
        self._renderer.add_text(
            key="status:main",
            text=status,
            x=status_box.x + 14.0,
            y=status_box.y + status_box.h / 2.0,
            font_size=16.0,
            color="#dbeafe",
            anchor="middle-left",
        )
        if state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            self._renderer.add_text(
                key="title:player",
                text="Player Board",
                x=80.0,
                y=132.0,
                font_size=20.0,
                color="#bfdbfe",
                anchor="bottom-left",
            )
        if state in (AppState.BATTLE, AppState.RESULT):
            self._renderer.add_text(
                key="title:enemy",
                text="Enemy Board",
                x=640.0,
                y=132.0,
                font_size=20.0,
                color="#bfdbfe",
                anchor="bottom-left",
            )
        if state is AppState.PLACEMENT_EDIT and len(placements) < len(ship_order):
            self._renderer.add_text(
                key="status:placement_hint",
                text=f"Drag and drop ships. Hold a ship and press R to rotate. Orientation: {placement_orientation.value}",
                x=640.0,
                y=status_box.y + status_box.h / 2.0,
                font_size=15.0,
                color="#bfdbfe",
                anchor="middle-left",
            )

    def _draw_placement_panel(self, placements: list[ShipPlacement], ship_order: list[ShipType]) -> None:
        panel = PLACEMENT_PANEL.panel_rect()
        panel_x = panel.x
        panel_y = panel.y
        panel_w = panel.w
        panel_h = panel.h
        self._renderer.add_rect("placement:panel", panel_x, panel_y, panel_w, panel_h, "#0f172a", z=1.0)
        self._renderer.add_text(
            key="placement:fleet_title",
            text="Ships",
            x=panel_x + panel_w / 2.0,
            y=panel_y + 18.0,
            font_size=16.0,
            anchor="top-center",
        )

        placed_types = {placement.ship_type for placement in placements}
        for index, ship_type in enumerate(ship_order):
            row = PLACEMENT_PANEL.row_rect(index)
            is_placed = ship_type in placed_types
            color = "#10b981" if is_placed else "#334155"
            self._renderer.add_rect(
                f"placement:shipbg:{ship_type.value}",
                row.x,
                row.y,
                row.w,
                row.h,
                color,
                z=1.1,
            )
            self._renderer.add_text(
                key=f"placement:ship:{ship_type.value}",
                text=f"{ship_type.value[:3]} ({ship_type.size})",
                x=panel_x + panel_w / 2.0,
                y=row.y + row.h / 2.0,
                font_size=13.0,
                anchor="middle-center",
                color="#e2e8f0",
            )

    def _draw_player_board(
        self,
        placements: list[ShipPlacement],
        session: GameSession | None,
        held_ship_type: ShipType | None,
        held_orientation: Orientation | None,
        held_grab_index: int,
        hover_cell: Coord | None,
        hover_x: float | None,
        hover_y: float | None,
    ) -> None:
        self._draw_board_frame(is_ai=False)
        player_board = session.player_board if session else None
        if player_board is not None:
            self._draw_ships_from_board(player_board, is_ai=False)
            if session:
                self._draw_shots(player_board, is_ai=False)
            return
        self._draw_ships_from_placements(placements)
        if held_ship_type is not None and held_orientation is not None:
            self._draw_held_ship_preview(
                held_ship_type,
                held_orientation,
                held_grab_index,
                hover_cell,
                hover_x,
                hover_y,
            )

    def _draw_ai_board(self, state: AppState, session: GameSession | None) -> None:
        self._draw_board_frame(is_ai=True)
        if session is None:
            return
        self._draw_shots(session.ai_board, is_ai=True)

    def _draw_board_frame(self, is_ai: bool) -> None:
        board_key = "ai" if is_ai else "player"
        rect = self._layout.board_rect(is_ai=is_ai)
        self._renderer.add_rect(f"board:bg:{board_key}", rect.x, rect.y, rect.w, rect.h, "#1e3a8a", z=0.1)
        self._renderer.add_grid(
            key=f"board:grid:{board_key}",
            x=rect.x,
            y=rect.y,
            width=rect.w,
            height=rect.h,
            lines=11,
            color="#60a5fa",
            z=0.2,
        )

    def _draw_ships_from_placements(self, placements: list[ShipPlacement]) -> None:
        for placement in placements:
            for coord in cells_for_placement(placement):
                cell_rect = self._layout.cell_rect(is_ai=False, coord=coord)
                self._renderer.add_rect(
                    f"ship:placement:{placement.ship_type.value}:{coord.row}:{coord.col}",
                    cell_rect.x + 2.0,
                    cell_rect.y + 2.0,
                    cell_rect.w - 4.0,
                    cell_rect.h - 4.0,
                    "#10b981",
                    z=0.3,
                )

    def _draw_ships_from_board(self, board: BoardState, is_ai: bool) -> None:
        board_key = "ai" if is_ai else "player"
        for row in range(board.size):
            for col in range(board.size):
                if int(board.ships[row, col]) == 0:
                    continue
                cell_rect = self._layout.cell_rect(is_ai=is_ai, coord=Coord(row=row, col=col))
                self._renderer.add_rect(
                    f"ship:{board_key}:{row}:{col}",
                    cell_rect.x + 2.0,
                    cell_rect.y + 2.0,
                    cell_rect.w - 4.0,
                    cell_rect.h - 4.0,
                    "#059669",
                    z=0.3,
                )

    def _draw_shots(self, board: BoardState, is_ai: bool) -> None:
        board_key = "ai" if is_ai else "player"
        for row in range(board.size):
            for col in range(board.size):
                value = int(board.shots[row, col])
                if value == 0:
                    continue
                cell_rect = self._layout.cell_rect(is_ai=is_ai, coord=Coord(row=row, col=col))
                color = "#e11d48" if value == 2 else "#f1f5f9"
                self._renderer.add_rect(
                    f"shot:{board_key}:{row}:{col}",
                    cell_rect.x + self._layout.cell_size * 0.3,
                    cell_rect.y + self._layout.cell_size * 0.3,
                    self._layout.cell_size * 0.4,
                    self._layout.cell_size * 0.4,
                    color,
                    z=0.4,
                )

    def _draw_held_ship_preview(
        self,
        ship_type: ShipType,
        orientation: Orientation,
        grab_index: int,
        hover_cell: Coord | None,
        hover_x: float | None,
        hover_y: float | None,
    ) -> None:
        if hover_cell is not None:
            bow_row = hover_cell.row - (grab_index if orientation is Orientation.VERTICAL else 0)
            bow_col = hover_cell.col - (grab_index if orientation is Orientation.HORIZONTAL else 0)
            for i in range(ship_type.size):
                row = bow_row + (i if orientation is Orientation.VERTICAL else 0)
                col = bow_col + (i if orientation is Orientation.HORIZONTAL else 0)
                if row < 0 or row >= 10 or col < 0 or col >= 10:
                    continue
                cell_rect = self._layout.cell_rect(is_ai=False, coord=Coord(row=row, col=col))
                self._renderer.add_rect(
                    f"held:preview:{ship_type.value}:{i}",
                    cell_rect.x + 2.0,
                    cell_rect.y + 2.0,
                    cell_rect.w - 4.0,
                    cell_rect.h - 4.0,
                    "#f59e0b",
                    z=0.35,
                )
            return
        if hover_x is None or hover_y is None:
            return
        # Off-board floating preview under cursor.
        for i in range(ship_type.size):
            dx = (i - grab_index) * 22.0 if orientation is Orientation.HORIZONTAL else 0.0
            dy = (i - grab_index) * 22.0 if orientation is Orientation.VERTICAL else 0.0
            self._renderer.add_rect(
                f"held:preview:float:{ship_type.value}:{i}",
                hover_x + dx - 9.0,
                hover_y + dy - 9.0,
                18.0,
                18.0,
                "#f59e0b",
                z=1.2,
            )

    def _draw_preset_manage(self, ui: AppUIState) -> None:
        panel = PRESET_PANEL.panel_rect()
        panel_x = panel.x
        panel_y = panel.y
        panel_w = panel.w
        panel_h = panel.h
        self._renderer.add_rect("presets:panel", panel_x, panel_y, panel_w, panel_h, "#0f172a", z=0.85)
        self._renderer.add_text(
            key="presets:title",
            text="Preset Manager",
            x=panel_x + 16.0,
            y=panel_y + 16.0,
            font_size=28.0,
            color="#dbeafe",
            anchor="top-left",
        )
        for idx, row in enumerate(ui.preset_rows):
            row_rect = PRESET_PANEL.row_rect(idx)
            self._renderer.add_rect(f"preset:row:{row.name}", row_rect.x, row_rect.y, row_rect.w, row_rect.h, "#111827", z=0.9)
            self._renderer.add_text(
                key=f"preset:name:{row.name}",
                text=_truncate(row.name, PRESET_PANEL.name_max_len),
                x=row_rect.x + PRESET_PANEL.name_x_pad,
                y=row_rect.y + PRESET_PANEL.name_y_pad,
                font_size=18.0,
                color="#e5e7eb",
                anchor="top-left",
            )
            preview = PRESET_PANEL.preview_rect(idx)
            self._draw_preset_preview(
                row.name,
                row.placements,
                x=preview.x,
                y=preview.y,
                cell=PRESET_PANEL.preview_cell,
            )
            edit_rect, rename_rect, delete_rect = PRESET_PANEL.action_button_rects(idx)
            self._renderer.add_rect(
                f"preset:btnbg:edit:{row.name}",
                edit_rect.x,
                edit_rect.y,
                edit_rect.w,
                edit_rect.h,
                "#1f6feb",
                z=1.0,
            )
            self._renderer.add_rect(
                f"preset:btnbg:rename:{row.name}",
                rename_rect.x,
                rename_rect.y,
                rename_rect.w,
                rename_rect.h,
                "#1f6feb",
                z=1.0,
            )
            self._renderer.add_rect(
                f"preset:btnbg:delete:{row.name}",
                delete_rect.x,
                delete_rect.y,
                delete_rect.w,
                delete_rect.h,
                "#b91c1c",
                z=1.0,
            )

    def _draw_new_game_setup(self, ui: AppUIState) -> None:
        panel = NEW_GAME_SETUP.panel_rect()
        self._renderer.add_rect("newgame:panel", panel.x, panel.y, panel.w, panel.h, "#0f172a", z=0.85)
        self._renderer.add_text(
            key="newgame:title",
            text="New Game Setup",
            x=panel.x + 20.0,
            y=panel.y + 20.0,
            font_size=30.0,
            color="#dbeafe",
            anchor="top-left",
        )
        self._renderer.add_text(
            key="newgame:difficulty_label",
            text="Difficulty",
            x=panel.x + 20.0,
            y=panel.y + 60.0,
            font_size=16.0,
            color="#bfdbfe",
            anchor="top-left",
        )
        diff_rect = NEW_GAME_SETUP.difficulty_rect()
        self._renderer.add_rect("newgame:diff:bg", diff_rect.x, diff_rect.y, diff_rect.w, diff_rect.h, "#1e293b", z=0.9)
        self._renderer.add_text(
            key="newgame:difficulty",
            text=ui.new_game_difficulty or "Normal",
            x=diff_rect.x + 12.0,
            y=diff_rect.y + diff_rect.h / 2.0,
            font_size=20.0,
            color="#e2e8f0",
            anchor="middle-left",
        )
        if ui.new_game_difficulty_open:
            for idx, name in enumerate(ui.new_game_difficulty_options):
                option = NEW_GAME_SETUP.difficulty_option_rect(idx)
                color = "#2563eb" if name == ui.new_game_difficulty else "#334155"
                self._renderer.add_rect(f"newgame:diff:opt:bg:{name}", option.x, option.y, option.w, option.h, color, z=0.95)
                self._renderer.add_text(
                    key=f"newgame:diff:opt:text:{name}",
                    text=name,
                    x=option.x + 10.0,
                    y=option.y + option.h / 2.0,
                    font_size=16.0,
                    color="#e2e8f0",
                    anchor="middle-left",
                    z=0.96,
                )

        list_rect = NEW_GAME_SETUP.preset_list_rect()
        self._renderer.add_rect("newgame:presets:bg", list_rect.x, list_rect.y, list_rect.w, list_rect.h, "#111827", z=0.88)
        self._renderer.add_text(
            key="newgame:presets:title",
            text="Available Presets",
            x=list_rect.x + 12.0,
            y=list_rect.y + 10.0,
            font_size=16.0,
            color="#bfdbfe",
            anchor="top-left",
            z=0.9,
        )
        for idx, name in enumerate(ui.new_game_visible_presets):
            row = NEW_GAME_SETUP.preset_row_rect(idx)
            color = "#2563eb" if name == ui.new_game_selected_preset else "#1f2937"
            self._renderer.add_rect(f"newgame:preset:row:{name}", row.x, row.y, row.w, row.h, color, z=0.9)
            self._renderer.add_text(
                key=f"newgame:preset:text:{name}",
                text=_truncate(name, 36),
                x=row.x + 12.0,
                y=row.y + row.h / 2.0,
                font_size=16.0,
                color="#e5e7eb",
                anchor="middle-left",
                z=0.92,
            )
        self._renderer.add_text(
            key="newgame:presets:hint",
            text="Scroll with mouse wheel while hovering this list",
            x=list_rect.x + 12.0,
            y=list_rect.y + list_rect.h + 12.0,
            font_size=13.0,
            color="#93c5fd",
            anchor="top-left",
            z=0.92,
        )

        random_btn = NEW_GAME_SETUP.random_button_rect()
        self._renderer.add_rect("newgame:random:bg", random_btn.x, random_btn.y, random_btn.w, random_btn.h, "#7c3aed", z=0.9)
        self._renderer.add_text(
            key="newgame:random:text",
            text="Generate Random Fleet",
            x=random_btn.x + random_btn.w / 2.0,
            y=random_btn.y + random_btn.h / 2.0,
            font_size=14.0,
            anchor="middle-center",
            z=0.92,
        )

        self._renderer.add_text(
            key="newgame:preview_title",
            text=f"Selected Setup: {ui.new_game_source or 'None'}",
            x=panel.x + 520.0,
            y=panel.y + 140.0,
            font_size=18.0,
            color="#bfdbfe",
            anchor="top-left",
        )
        preview_x, preview_y = NEW_GAME_SETUP.preview_origin()
        self._draw_preset_preview("newgame:selected", ui.new_game_preview, x=preview_x, y=preview_y, cell=NEW_GAME_SETUP.preview_cell)

    def _draw_preset_preview(self, key_prefix: str, placements: list[ShipPlacement], x: float, y: float, cell: float) -> None:
        self._renderer.add_rect(f"preset:preview:bg:{key_prefix}", x, y, cell * 10, cell * 10, "#1e3a8a", z=1.0)
        for placement in placements:
            for coord in cells_for_placement(placement):
                self._renderer.add_rect(
                    f"preset:preview:cell:{key_prefix}:{coord.row}:{coord.col}",
                    x + coord.col * cell + 0.5,
                    y + coord.row * cell + 0.5,
                    cell - 1.0,
                    cell - 1.0,
                    "#10b981",
                    z=1.1,
                )

def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def _is_new_game_custom_button(button_id: str) -> bool:
    return (
        button_id == "new_game_toggle_difficulty"
        or button_id == "new_game_randomize"
        or button_id.startswith("new_game_diff_option:")
        or button_id.startswith("new_game_select_preset:")
    )

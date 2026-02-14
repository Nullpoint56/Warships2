"""Retained-mode game rendering for Warships."""

from __future__ import annotations

import logging

from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.board import BoardState
from warships.core.models import Coord, Orientation, ShipPlacement, ShipType, Turn
from warships.core.rules import GameSession
from warships.ui.board_view import BoardLayout
from warships.ui.overlays import Button, button_label
from warships.ui.scene import SceneRenderer

logger = logging.getLogger(__name__)


class GameView:
    """Draws game state using retained keyed scene nodes."""

    def __init__(self, renderer: SceneRenderer, layout: BoardLayout) -> None:
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
        if not self._static_initialized:
            self._build_static_layer()
        self._renderer.begin_frame()

        labels = self._draw_buttons(ui.buttons)
        if ui.state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            self._draw_player_board(ui.placements, ui.session)
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            self._draw_ai_board(ui.state, ui.session)
        if ui.state is AppState.PLACEMENT_EDIT:
            self._draw_placement_panel(ui.placements, ui.ship_order)

        self._draw_status_bar(ui.state, ui.status, ui.placement_orientation, ui.placements, ui.ship_order)
        self._renderer.set_title(f"Warships V1 | {ui.status}")

        if debug_ui and labels != debug_labels_state:
            logger.debug("ui_button_labels labels=%s", labels)
        self._renderer.end_frame()
        return labels

    def _build_static_layer(self) -> None:
        self._renderer.add_rect("static:bg", 0, 0, 1200, 720, "#0b132b", static=True)
        self._static_initialized = True

    def _draw_buttons(self, buttons: list[Button]) -> list[str]:
        labels: list[str] = []
        for button in buttons:
            color = "#1f6feb" if button.enabled else "#384151"
            self._renderer.add_rect(
                f"button:bg:{button.id}",
                button.x,
                button.y,
                button.w,
                button.h,
                color,
                z=1.0,
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
                z=3.0,
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
        self._renderer.add_rect("status:bg", 60.0, 650.0, 1080.0, 44.0, "#172554", z=1.0)
        self._renderer.add_text(
            key="status:main",
            text=status,
            x=74.0,
            y=675.0,
            font_size=16.0,
            color="#dbeafe",
            anchor="middle-left",
        )
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
            next_ship = ship_order[len(placements)]
            self._renderer.add_text(
                key="status:placement_hint",
                text=f"Place: {next_ship.value} ({next_ship.size}) | Orientation: {placement_orientation.value}",
                x=640.0,
                y=675.0,
                font_size=15.0,
                color="#bfdbfe",
                anchor="middle-left",
            )

    def _draw_placement_panel(self, placements: list[ShipPlacement], ship_order: list[ShipType]) -> None:
        panel_x = 1080.0
        panel_y = 150.0
        panel_w = 90.0
        panel_h = 420.0
        self._renderer.add_rect("placement:panel", panel_x, panel_y, panel_w, panel_h, "#0f172a", z=1.0)
        self._renderer.add_text(
            key="placement:fleet_title",
            text="Fleet",
            x=panel_x + panel_w / 2.0,
            y=panel_y + 18.0,
            font_size=16.0,
            anchor="top-center",
        )

        placed_types = {placement.ship_type for placement in placements}
        for index, ship_type in enumerate(ship_order):
            y = panel_y + 55.0 + index * 70.0
            is_placed = ship_type in placed_types
            color = "#10b981" if is_placed else "#334155"
            self._renderer.add_rect(
                f"placement:shipbg:{ship_type.value}",
                panel_x + 10.0,
                y,
                panel_w - 20.0,
                24.0,
                color,
                z=1.1,
            )
            self._renderer.add_text(
                key=f"placement:ship:{ship_type.value}",
                text=f"{ship_type.value[:3]} ({ship_type.size})",
                x=panel_x + panel_w / 2.0,
                y=y + 12.0,
                font_size=13.0,
                anchor="middle-center",
                color="#e2e8f0",
            )

    def _draw_player_board(self, placements: list[ShipPlacement], session: GameSession | None) -> None:
        self._draw_board_frame(is_ai=False)
        player_board = session.player_board if session else None
        if player_board is not None:
            self._draw_ships_from_board(player_board, is_ai=False)
            self._draw_shots(player_board, is_ai=False)
        else:
            self._draw_ships_from_placements(placements)

    def _draw_ai_board(self, state: AppState, session: GameSession | None) -> None:
        self._draw_board_frame(is_ai=True)
        if session is None:
            return
        self._draw_shots(session.ai_board, is_ai=True)
        if state is AppState.RESULT and session.winner is Turn.AI:
            self._draw_ships_from_board(session.ai_board, is_ai=True)

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
            for coord in _cells_for_ship(placement):
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


def _cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    cells: list[Coord] = []
    for offset in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            cells.append(Coord(row=placement.bow.row, col=placement.bow.col + offset))
        else:
            cells.append(Coord(row=placement.bow.row + offset, col=placement.bow.col))
    return cells

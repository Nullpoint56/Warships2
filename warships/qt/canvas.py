"""Qt canvas for board rendering and placement interactions."""

from __future__ import annotations

from collections.abc import Callable

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.models import Coord, Orientation
from warships.qt.common import DESIGN_H, DESIGN_W, cells_for_ship, status_color
from warships.ui.board_view import BoardLayout, Rect
from warships.ui.layout_metrics import PLACEMENT_PANEL, PROMPT, status_rect
from warships.ui.overlays import Button, button_label

try:
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
    from PyQt6.QtWidgets import QWidget
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


class GameCanvas(QWidget):
    def __init__(self, controller: GameController, layout: BoardLayout, on_button: Callable[[str], None]) -> None:
        super().__init__()
        self._controller = controller
        self._layout = layout
        self._on_button = on_button
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._hover_design: tuple[float, float] | None = None

    def _update_viewport(self) -> None:
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        self._scale = min(w / DESIGN_W, h / DESIGN_H)
        self._offset_x = (w - DESIGN_W * self._scale) * 0.5
        self._offset_y = (h - DESIGN_H * self._scale) * 0.5

    def _to_design(self, x: float, y: float) -> tuple[float, float]:
        self._update_viewport()
        return (x - self._offset_x) / self._scale, (y - self._offset_y) / self._scale

    def _to_screen_rect(self, r: Rect) -> QRectF:
        self._update_viewport()
        return QRectF(
            self._offset_x + r.x * self._scale,
            self._offset_y + r.y * self._scale,
            r.w * self._scale,
            r.h * self._scale,
        )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        ui = self._controller.ui_state()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0b132b"))
        if ui.state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            self._draw_board(painter, ui, is_ai=False)
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            self._draw_board(painter, ui, is_ai=True)
        if ui.state is AppState.PLACEMENT_EDIT:
            self._draw_placement_panel(painter, ui)
        for b in ui.buttons:
            self._draw_button(painter, b)
        if ui.prompt is not None:
            self._draw_prompt(painter)
        s = status_rect()
        self._draw_rect(painter, s, "#172554")
        self._draw_text(painter, ui.status, s.x + 10, s.y + s.h / 2 + 5, 13, status_color(ui.status))
        if ui.state is AppState.PLACEMENT_EDIT:
            self._draw_text(
                painter,
                "Left click: pick/place  Right click: remove  R: rotate held  D: delete held  Save enabled after all ships",
                s.x + 10,
                s.y + s.h + 18,
                11,
                "#93c5fd",
            )
        painter.end()

    def _draw_rect(self, painter: QPainter, r: Rect, color: str) -> None:
        sr = self._to_screen_rect(r)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRect(sr)

    def _draw_text(self, painter: QPainter, text: str, x: float, y: float, size: int = 14, color: str = "#e5e7eb") -> None:
        self._update_viewport()
        painter.setPen(QColor(color))
        painter.setFont(QFont("Segoe UI", max(8, int(size * self._scale))))
        painter.drawText(QPointF(self._offset_x + x * self._scale, self._offset_y + y * self._scale), text)

    def _draw_button(self, painter: QPainter, b: Button) -> None:
        color = "#1f6feb" if b.enabled else "#374151"
        self._draw_rect(painter, Rect(b.x, b.y, b.w, b.h), color)
        self._draw_text(painter, button_label(b.id), b.x + 10, b.y + b.h / 2 + 5, 12)

    def _draw_board(self, painter: QPainter, ui: AppUIState, is_ai: bool) -> None:
        br = self._layout.board_rect(is_ai)
        self._draw_rect(painter, br, "#1e3a8a")
        sr = self._to_screen_rect(br)
        painter.setPen(QPen(QColor("#60a5fa"), 1))
        for i in range(11):
            x = sr.x() + (sr.width() / 10) * i
            y = sr.y() + (sr.height() / 10) * i
            painter.drawLine(QPointF(x, sr.y()), QPointF(x, sr.y() + sr.height()))
            painter.drawLine(QPointF(sr.x(), y), QPointF(sr.x() + sr.width(), y))

        board = None if ui.session is None else (ui.session.ai_board if is_ai else ui.session.player_board)
        if board is not None:
            for r in range(10):
                for c in range(10):
                    cell = self._layout.cell_rect(is_ai, Coord(r, c))
                    if not is_ai and int(board.ships[r, c]) != 0:
                        self._draw_rect(painter, Rect(cell.x + 2, cell.y + 2, cell.w - 4, cell.h - 4), "#059669")
                    shot = int(board.shots[r, c])
                    if shot != 0:
                        self._draw_rect(painter, Rect(cell.x + 14, cell.y + 14, cell.w - 28, cell.h - 28), "#e11d48" if shot == 2 else "#f1f5f9")
        elif not is_ai:
            for placement in ui.placements:
                for cell in cells_for_ship(placement):
                    rect = self._layout.cell_rect(False, cell)
                    self._draw_rect(painter, Rect(rect.x + 2, rect.y + 2, rect.w - 4, rect.h - 4), "#10b981")
            self._draw_held_preview(painter, ui)

    def _draw_placement_panel(self, painter: QPainter, ui: AppUIState) -> None:
        panel = PLACEMENT_PANEL.panel_rect()
        self._draw_rect(painter, panel, "#0f172a")
        placed = {p.ship_type for p in ui.placements}
        for idx, ship in enumerate(ui.ship_order):
            row = PLACEMENT_PANEL.row_rect(idx)
            color = "#10b981" if ship in placed else "#334155"
            if self._hover_design is not None and row.contains(self._hover_design[0], self._hover_design[1]):
                color = "#f59e0b" if ship not in placed else "#22c55e"
            self._draw_rect(painter, row, color)
            self._draw_text(painter, f"{ship.value[:3]} ({ship.size})", row.x + 4, row.y + row.h / 2 + 4, 11)

    def _draw_held_preview(self, painter: QPainter, ui: AppUIState) -> None:
        if ui.held_ship_type is None or ui.held_ship_orientation is None:
            return
        if ui.hover_cell is not None:
            bow_row = ui.hover_cell.row - (ui.held_grab_index if ui.held_ship_orientation is Orientation.VERTICAL else 0)
            bow_col = ui.hover_cell.col - (ui.held_grab_index if ui.held_ship_orientation is Orientation.HORIZONTAL else 0)
            for i in range(ui.held_ship_type.size):
                row = bow_row + (i if ui.held_ship_orientation is Orientation.VERTICAL else 0)
                col = bow_col + (i if ui.held_ship_orientation is Orientation.HORIZONTAL else 0)
                if not (0 <= row < 10 and 0 <= col < 10):
                    continue
                rect = self._layout.cell_rect(False, Coord(row, col))
                self._draw_rect(painter, Rect(rect.x + 2, rect.y + 2, rect.w - 4, rect.h - 4), "#f59e0b")
            return
        if ui.hover_x is None or ui.hover_y is None:
            return
        for i in range(ui.held_ship_type.size):
            dx = (i - ui.held_grab_index) * 22.0 if ui.held_ship_orientation is Orientation.HORIZONTAL else 0.0
            dy = (i - ui.held_grab_index) * 22.0 if ui.held_ship_orientation is Orientation.VERTICAL else 0.0
            self._draw_rect(
                painter,
                Rect(ui.hover_x + dx - 9.0, ui.hover_y + dy - 9.0, 18.0, 18.0),
                "#f59e0b",
            )

    def _draw_prompt(self, painter: QPainter) -> None:
        overlay = PROMPT.overlay_rect()
        panel = PROMPT.panel_rect()
        self._draw_rect(painter, overlay, "#000000")
        self._draw_rect(painter, panel, "#1f2937")

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        x, y = self._to_design(event.position().x(), event.position().y())
        ui = self._controller.ui_state()
        button_num = 1 if event.button() == Qt.MouseButton.LeftButton else 2 if event.button() == Qt.MouseButton.RightButton else 0
        if button_num == 1:
            for b in ui.buttons:
                if b.enabled and b.contains(x, y):
                    self._on_button(b.id)
                    return
            if ui.state is AppState.BATTLE:
                ai_cell = self._layout.screen_to_cell(True, x, y)
                if ai_cell is not None and self._controller.handle_board_click(BoardCellPressed(True, ai_cell)):
                    self.update()
                    return
        if self._controller.handle_pointer_down(x, y, button_num):
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        x, y = self._to_design(event.position().x(), event.position().y())
        self._hover_design = (x, y)
        ui = self._controller.ui_state()
        tip = ""
        for b in ui.buttons:
            if b.contains(x, y) and not b.enabled and b.id == "save_preset":
                tip = "Place all ships to enable Save Preset."
                break
        self.setToolTip(tip)
        if self._controller.handle_pointer_move(PointerMoved(x=x, y=y)):
            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        x, y = self._to_design(event.position().x(), event.position().y())
        button_num = 1 if event.button() == Qt.MouseButton.LeftButton else 2 if event.button() == Qt.MouseButton.RightButton else 0
        if self._controller.handle_pointer_release(PointerReleased(x=x, y=y, button=button_num)):
            self.update()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key_map = {
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Escape: "escape",
            Qt.Key.Key_R: "r",
            Qt.Key.Key_D: "d",
        }
        changed = False
        if event.key() in key_map:
            changed = self._controller.handle_key_pressed(KeyPressed(key_map[event.key()]))
        text = event.text()
        if text and text.isprintable():
            changed = self._controller.handle_char_typed(CharTyped(text)) or changed
        if changed:
            self.update()

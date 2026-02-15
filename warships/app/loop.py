"""PyQt application loop with native menu/settings widgets."""

from __future__ import annotations

import os
import random
from pathlib import Path

from warships.app.controller import GameController
from warships.app.events import BoardCellPressed, ButtonPressed, CharTyped, KeyPressed, PointerMoved, PointerReleased
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.models import Coord, Orientation, ShipPlacement
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService
from warships.ui.board_view import BoardLayout, Rect
from warships.ui.layout_metrics import PLACEMENT_PANEL, PROMPT, root_rect, status_rect
from warships.ui.overlays import Button, button_label

try:
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStackedWidget,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


DESIGN_W = 1200.0
DESIGN_H = 720.0


class _FleetPreviewWidget(QWidget):
    def __init__(self, min_size: int = 220) -> None:
        super().__init__()
        self._placements: list[ShipPlacement] = []
        self.setMinimumSize(min_size, min_size)

    def set_placements(self, placements: list[ShipPlacement]) -> None:
        self._placements = list(placements)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e3a8a"))
        w = self.width()
        h = self.height()
        cell = min(w, h) / 10.0
        ox = (w - cell * 10.0) * 0.5
        oy = (h - cell * 10.0) * 0.5
        painter.setPen(QPen(QColor("#60a5fa"), 1))
        for i in range(11):
            x = ox + i * cell
            y = oy + i * cell
            painter.drawLine(QPointF(x, oy), QPointF(x, oy + 10.0 * cell))
            painter.drawLine(QPointF(ox, y), QPointF(ox + 10.0 * cell, y))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#10b981"))
        for placement in self._placements:
            for c in _cells_for_ship(placement):
                painter.drawRect(QRectF(ox + c.col * cell + 1.0, oy + c.row * cell + 1.0, cell - 2.0, cell - 2.0))
        painter.end()


class _MainMenuPage(QWidget):
    def __init__(self, on_button: callable) -> None:
        super().__init__()
        self._on_button = on_button
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("Warships")
        title.setStyleSheet("font-size: 28px; color: #dbeafe;")
        layout.addWidget(title)
        subtitle = QLabel("Classic naval tactics. Configure, place, and sink.")
        subtitle.setStyleSheet("color: #93c5fd;")
        layout.addWidget(subtitle)
        row = QHBoxLayout()
        self._new = QPushButton("New Game")
        self._manage = QPushButton("Manage Presets")
        self._quit = QPushButton("Quit")
        for button in (self._new, self._manage, self._quit):
            button.setMinimumHeight(48)
        row.addWidget(self._new)
        row.addWidget(self._manage)
        row.addWidget(self._quit)
        layout.addLayout(row)
        self._status = QLabel("")
        self._status.setStyleSheet("color: #bfdbfe;")
        layout.addWidget(self._status)
        layout.addStretch(1)
        self._new.clicked.connect(lambda: self._on_button("new_game"))
        self._manage.clicked.connect(lambda: self._on_button("manage_presets"))
        self._quit.clicked.connect(lambda: self._on_button("quit"))
        self.setTabOrder(self._new, self._manage)
        self.setTabOrder(self._manage, self._quit)

    def sync(self, ui: AppUIState) -> None:
        self._status.setText(ui.status)
        self._status.setStyleSheet(f"color: {_status_color(ui.status)};")


class _NewGamePage(QWidget):
    def __init__(self, on_button: callable) -> None:
        super().__init__()
        self._on_button = on_button
        self._syncing = False
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        title = QLabel("New Game Setup")
        title.setStyleSheet("font-size: 24px; color: #dbeafe;")
        root.addWidget(title)
        helper = QLabel("Choose AI difficulty, select a preset or generate a random fleet, then start.")
        helper.setStyleSheet("color: #93c5fd;")
        root.addWidget(helper)

        top = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        left.addWidget(QLabel("Difficulty"))
        self._difficulty = QComboBox()
        self._difficulty.setMinimumHeight(40)
        self._difficulty.currentTextChanged.connect(self._difficulty_changed)
        left.addWidget(self._difficulty)

        left.addWidget(QLabel("Available Presets"))
        self._presets = QListWidget()
        self._presets.setMinimumHeight(280)
        self._presets.itemClicked.connect(self._preset_clicked)
        left.addWidget(self._presets, 1)
        self._presets.setToolTip("Scroll inside this list with the mouse wheel.")

        self._random = QPushButton("Generate Random Fleet")
        self._random.setMinimumHeight(44)
        self._random.clicked.connect(lambda: self._on_button("new_game_randomize"))
        left.addWidget(self._random)

        self._start = QPushButton("Start Game")
        self._start.clicked.connect(lambda: self._on_button("start_game"))
        self._back = QPushButton("Main Menu")
        self._back.clicked.connect(lambda: self._on_button("back_main"))
        self._start.setMinimumHeight(44)
        self._back.setMinimumHeight(44)
        row = QHBoxLayout()
        row.addWidget(self._start)
        row.addWidget(self._back)
        left.addLayout(row)

        right.addWidget(QLabel("Fleet Preview"))
        self._source = QLabel("Selected Setup: None")
        self._source.setStyleSheet("color: #bfdbfe;")
        right.addWidget(self._source)
        self._preview = _FleetPreviewWidget()
        right.addWidget(self._preview, 1)

        top.addLayout(left, 2)
        top.addLayout(right, 1)
        root.addLayout(top, 1)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #dbeafe;")
        root.addWidget(self._status)
        self.setTabOrder(self._difficulty, self._presets)
        self.setTabOrder(self._presets, self._random)
        self.setTabOrder(self._random, self._start)
        self.setTabOrder(self._start, self._back)

    def _difficulty_changed(self, value: str) -> None:
        if self._syncing:
            return
        self._on_button(f"new_game_diff_option:{value}")

    def _preset_clicked(self, item: QListWidgetItem) -> None:
        self._on_button(f"new_game_select_preset:{item.text()}")

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        # Let list widget do native scrolling.
        super().wheelEvent(event)

    def sync(self, ui: AppUIState) -> None:
        self._syncing = True
        self._difficulty.clear()
        self._difficulty.addItems(ui.new_game_difficulty_options)
        if ui.new_game_difficulty:
            idx = self._difficulty.findText(ui.new_game_difficulty)
            if idx >= 0:
                self._difficulty.setCurrentIndex(idx)
        self._presets.clear()
        for row in ui.preset_rows:
            item = QListWidgetItem(row.name)
            self._presets.addItem(item)
            if row.name == ui.new_game_selected_preset:
                item.setSelected(True)
        self._source.setText(f"Selected Setup: {ui.new_game_source or 'None'}")
        self._preview.set_placements(ui.new_game_preview)
        self._status.setText(ui.status)
        self._status.setStyleSheet(f"color: {_status_color(ui.status)};")
        can_start = ui.new_game_source is not None and bool(ui.new_game_preview)
        self._start.setEnabled(can_start)
        self._start.setToolTip("" if can_start else "Select a preset or generate a random fleet first.")
        self._syncing = False


class _PresetManagerPage(QWidget):
    def __init__(self, on_button: callable) -> None:
        super().__init__()
        self._on_button = on_button
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Preset Manager")
        title.setStyleSheet("font-size: 24px; color: #dbeafe;")
        root.addWidget(title)
        self._list = QListWidget()
        self._list.setMinimumHeight(360)
        root.addWidget(self._list, 1)
        controls = QHBoxLayout()
        self._create = QPushButton("Create Preset")
        self._edit = QPushButton("Edit")
        self._rename = QPushButton("Rename")
        self._delete = QPushButton("Delete")
        self._back = QPushButton("Main Menu")
        for b in (self._create, self._edit, self._rename, self._delete, self._back):
            b.setMinimumHeight(42)
            controls.addWidget(b)
        root.addLayout(controls)
        self._status = QLabel("")
        self._status.setStyleSheet("color: #dbeafe;")
        root.addWidget(self._status)

        self._create.clicked.connect(lambda: self._on_button("create_preset"))
        self._back.clicked.connect(lambda: self._on_button("back_main"))
        self._edit.clicked.connect(lambda: self._for_selected("preset_edit:"))
        self._rename.clicked.connect(lambda: self._for_selected("preset_rename:"))
        self._delete.clicked.connect(self._confirm_delete)
        self.setTabOrder(self._list, self._create)
        self.setTabOrder(self._create, self._edit)
        self.setTabOrder(self._edit, self._rename)
        self.setTabOrder(self._rename, self._delete)
        self.setTabOrder(self._delete, self._back)

    def _for_selected(self, prefix: str) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(name, str):
            self._on_button(prefix + name)

    def _confirm_delete(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(name, str):
            return
        answer = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._on_button(f"preset_delete:{name}")

    def sync(self, ui: AppUIState) -> None:
        selected_item = self._list.currentItem()
        selected = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item is not None else None
        self._list.clear()
        for row in ui.preset_rows:
            it = QListWidgetItem("")
            it.setData(Qt.ItemDataRole.UserRole, row.name)
            it.setSizeHint(QRectF(0.0, 0.0, 300.0, 72.0).toRect().size())
            self._list.addItem(it)
            self._list.setItemWidget(it, _PresetListItemWidget(row.name, row.placements))
            if selected == row.name:
                it.setSelected(True)
        self._status.setText(ui.status)
        self._status.setStyleSheet(f"color: {_status_color(ui.status)};")


class _PresetListItemWidget(QWidget):
    def __init__(self, name: str, placements: list[ShipPlacement]) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(10)
        preview = _FleetPreviewWidget(min_size=56)
        preview.setFixedSize(56, 56)
        preview.set_placements(placements)
        title = QLabel(name)
        title.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        row.addWidget(preview, 0)
        row.addWidget(title, 1)


class _GameCanvas(QWidget):
    def __init__(self, controller: GameController, layout: BoardLayout, on_button: callable) -> None:
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
            self._draw_prompt(painter, ui)
        s = status_rect()
        self._draw_rect(painter, s, "#172554")
        self._draw_text(painter, ui.status, s.x + 10, s.y + s.h / 2 + 5, 13, _status_color(ui.status))
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
                for cell in _cells_for_ship(placement):
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

    def _draw_prompt(self, painter: QPainter, ui: AppUIState) -> None:
        del ui
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


class _MainWindow(QMainWindow):
    def __init__(self, controller: GameController) -> None:
        super().__init__()
        self._controller = controller
        self._layout = BoardLayout()
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._main = _MainMenuPage(self._click_button)
        self._new = _NewGamePage(self._click_button)
        self._presets = _PresetManagerPage(self._click_button)
        self._canvas = _GameCanvas(controller, self._layout, self._click_button)
        self._stack.addWidget(self._main)
        self._stack.addWidget(self._new)
        self._stack.addWidget(self._presets)
        self._stack.addWidget(self._canvas)
        self.setWindowTitle("Warships V1")

    def _click_button(self, button_id: str) -> None:
        if self._controller.handle_button(ButtonPressed(button_id)):
            self._sync_ui()

    def _sync_prompt(self, ui: AppUIState) -> None:
        if ui.prompt is None:
            return
        if ui.prompt.confirm_button_id == "prompt_confirm_overwrite":
            answer = QMessageBox.question(
                self,
                ui.prompt.title,
                f"Overwrite preset '{ui.prompt.value}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._controller.handle_button(ButtonPressed(ui.prompt.confirm_button_id))
            else:
                self._controller.handle_button(ButtonPressed(ui.prompt.cancel_button_id))
            return
        text, ok = QInputDialog.getText(self, ui.prompt.title, ui.prompt.title, text=ui.prompt.value)
        if not ok:
            self._controller.handle_button(ButtonPressed(ui.prompt.cancel_button_id))
            return
        for _ in range(len(ui.prompt.value)):
            self._controller.handle_key_pressed(KeyPressed("backspace"))
        for ch in text:
            self._controller.handle_char_typed(CharTyped(ch))
        self._controller.handle_key_pressed(KeyPressed("enter"))

    def _sync_ui(self) -> None:
        ui = self._controller.ui_state()
        while ui.prompt is not None:
            before = (ui.prompt.title, ui.prompt.value, ui.prompt.confirm_button_id)
            self._sync_prompt(ui)
            ui = self._controller.ui_state()
            after_prompt = ui.prompt
            if after_prompt is not None:
                after = (after_prompt.title, after_prompt.value, after_prompt.confirm_button_id)
                if after == before:
                    break
        if ui.state is AppState.MAIN_MENU:
            self._main.sync(ui)
            self._stack.setCurrentWidget(self._main)
        elif ui.state is AppState.NEW_GAME_SETUP:
            self._new.sync(ui)
            self._stack.setCurrentWidget(self._new)
        elif ui.state is AppState.PRESET_MANAGE:
            self._presets.sync(ui)
            self._stack.setCurrentWidget(self._presets)
        else:
            self._stack.setCurrentWidget(self._canvas)
            self._canvas.update()
            self._canvas.setFocus()
        if ui.is_closing:
            QApplication.instance().quit()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        ui = self._controller.ui_state()
        if event.key() == Qt.Key.Key_Escape:
            if ui.state is AppState.NEW_GAME_SETUP:
                self._click_button("back_main")
                return
            if ui.state is AppState.PRESET_MANAGE:
                self._click_button("back_main")
                return
            if ui.state is AppState.PLACEMENT_EDIT:
                self._click_button("back_to_presets")
                return
            if ui.state is AppState.BATTLE:
                self._click_button("back_main")
                return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            if ui.state is AppState.MAIN_MENU:
                self._click_button("new_game")
                return
            if ui.state is AppState.NEW_GAME_SETUP:
                self._click_button("start_game")
                return
            if ui.state is AppState.PRESET_MANAGE:
                self._click_button("create_preset")
                return
            if ui.state is AppState.PLACEMENT_EDIT:
                self._click_button("save_preset")
                return
            if ui.state is AppState.RESULT:
                self._click_button("play_again")
                return
        super().keyPressEvent(event)


class AppLoop:
    def __init__(self) -> None:
        preset_service = PresetService(PresetRepository(Path("data/presets")))
        debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        self._controller = GameController(preset_service=preset_service, rng=random.Random(), debug_ui=debug_ui)
        self._app = QApplication.instance() or QApplication([])
        self._app.setStyleSheet(
            """
            QWidget { font-size: 16px; }
            QLabel { color: #e2e8f0; }
            QPushButton { padding: 10px 16px; }
            QComboBox { padding: 6px 8px; }
            QListWidget { background: #111827; color: #e5e7eb; }
            """
        )
        self._window = _MainWindow(self._controller)

    def run(self) -> None:
        mode = os.getenv("WARSHIPS_WINDOW_MODE", "windowed").lower()
        if mode == "fullscreen":
            self._window.showFullScreen()
        elif mode in {"maximized", "borderless"}:
            self._window.showMaximized()
        else:
            self._window.resize(1280, 800)
            self._window.show()
        self._window._sync_ui()  # type: ignore[attr-defined]
        self._app.exec()


def _cells_for_ship(placement: ShipPlacement) -> list[Coord]:
    cells: list[Coord] = []
    for offset in range(placement.ship_type.size):
        if placement.orientation is Orientation.HORIZONTAL:
            cells.append(Coord(row=placement.bow.row, col=placement.bow.col + offset))
        else:
            cells.append(Coord(row=placement.bow.row + offset, col=placement.bow.col))
    return cells


def _status_color(status: str) -> str:
    low = status.lower()
    if any(word in low for word in ("failed", "error", "invalid", "cannot", "duplicate")):
        return "#fca5a5"
    if any(word in low for word in ("saved", "renamed", "deleted", "started", "placed", "selected", "generated", "win")):
        return "#86efac"
    return "#dbeafe"

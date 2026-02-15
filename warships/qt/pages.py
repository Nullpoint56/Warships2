"""Qt pages for menu and setup flows."""

from __future__ import annotations

from collections.abc import Callable

from warships.app.ui_state import AppUIState
from warships.core.models import ShipPlacement
from warships.qt.common import cells_for_ship, status_color

try:
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QPainter, QPen
    from PyQt6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


class FleetPreviewWidget(QWidget):
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
            for c in cells_for_ship(placement):
                painter.drawRect(QRectF(ox + c.col * cell + 1.0, oy + c.row * cell + 1.0, cell - 2.0, cell - 2.0))
        painter.end()


class MainMenuPage(QWidget):
    def __init__(self, on_button: Callable[[str], None]) -> None:
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
        self._status.setStyleSheet(f"color: {status_color(ui.status)};")


class NewGamePage(QWidget):
    def __init__(self, on_button: Callable[[str], None], on_scroll: Callable[[float], bool] | None = None) -> None:
        super().__init__()
        self._on_button = on_button
        self._on_scroll = on_scroll
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
        self._preview = FleetPreviewWidget()
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
        if self._on_scroll is not None:
            changed = self._on_scroll(float(event.angleDelta().y()))
            if changed:
                event.accept()
                return
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
        self._status.setStyleSheet(f"color: {status_color(ui.status)};")
        can_start = ui.new_game_source is not None and bool(ui.new_game_preview)
        self._start.setEnabled(can_start)
        self._start.setToolTip("" if can_start else "Select a preset or generate a random fleet first.")
        self._syncing = False


class PresetListItemWidget(QWidget):
    def __init__(self, name: str, placements: list[ShipPlacement]) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(10)
        preview = FleetPreviewWidget(min_size=56)
        preview.setFixedSize(56, 56)
        preview.set_placements(placements)
        title = QLabel(name)
        title.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        row.addWidget(preview, 0)
        row.addWidget(title, 1)


class PresetManagerPage(QWidget):
    def __init__(self, on_button: Callable[[str], None]) -> None:
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
            self._list.setItemWidget(it, PresetListItemWidget(row.name, row.placements))
            if selected == row.name:
                it.setSelected(True)
        self._status.setText(ui.status)
        self._status.setStyleSheet(f"color: {status_color(ui.status)};")

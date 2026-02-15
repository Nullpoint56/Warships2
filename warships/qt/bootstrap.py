"""Qt frontend bootstrap and runtime wiring."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.frontend import FrontendBundle
from warships.qt.window import MainWindow, QtFrontendWindow

try:
    from PyQt6.QtWidgets import QApplication
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the UI. Install dependency 'PyQt6'.") from exc


def create_qt_frontend(controller: GameController) -> FrontendBundle:
    """Build Qt window adapter and event-loop runner."""
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(
        """
        QWidget { font-size: 16px; }
        QLabel { color: #e2e8f0; }
        QPushButton { padding: 10px 16px; }
        QComboBox { padding: 6px 8px; }
        QListWidget { background: #111827; color: #e5e7eb; }
        """
    )
    window = QtFrontendWindow(MainWindow(controller))
    return FrontendBundle(window=window, run_event_loop=lambda: app.exec())


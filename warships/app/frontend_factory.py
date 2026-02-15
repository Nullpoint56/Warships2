"""Frontend factory and selection boundary."""

from __future__ import annotations

import os

from warships.app.controller import GameController
from warships.app.frontend import FrontendBundle


def create_frontend(controller: GameController) -> FrontendBundle:
    """Create the configured frontend bundle."""
    frontend = os.getenv("WARSHIPS_FRONTEND", "qt").strip().lower()
    if frontend in {"qt", "pyqt", "pyqt6"}:
        from warships.qt.bootstrap import create_qt_frontend

        return create_qt_frontend(controller)
    raise ValueError(f"Unsupported frontend '{frontend}'.")


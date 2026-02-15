"""Frontend factory and selection boundary."""

from __future__ import annotations

import os

from warships.app.controller import GameController
from warships.app.frontend import FrontendBundle


def create_frontend(controller: GameController) -> FrontendBundle:
    """Create the configured frontend bundle."""
    frontend = os.getenv("WARSHIPS_FRONTEND", "pygfx").strip().lower()
    if frontend not in {"pygfx", "gfx", "wgpu"}:
        raise ValueError(f"Unsupported frontend '{frontend}'.")
    from warships.ui.bootstrap import create_pygfx_frontend

    return create_pygfx_frontend(controller)

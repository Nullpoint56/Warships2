"""Frontend factory and selection boundary."""

from __future__ import annotations

from warships.app.controller import GameController
from warships.app.frontend import FrontendBundle


def create_frontend(controller: GameController) -> FrontendBundle:
    """Create the pygfx frontend bundle."""
    from warships.engine.runtime.pygfx_frontend import create_pygfx_frontend

    return create_pygfx_frontend(controller)

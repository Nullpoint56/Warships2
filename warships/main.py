"""Application entry point."""

import logging
import os

from warships.game.app.engine_hosted_runtime import run_engine_hosted_app
from warships.game.infra.config import load_env_file
from warships.game.infra.logging import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Warships application."""
    load_env_file()
    setup_logging()
    if os.getenv("WARSHIPS_DEBUG_INPUT") == "1" or os.getenv("WARSHIPS_DEBUG_UI") == "1":
        logger.info(
            "Debug flags enabled",
            extra={
                "warships_debug_input": os.getenv("WARSHIPS_DEBUG_INPUT", "0"),
                "warships_debug_ui": os.getenv("WARSHIPS_DEBUG_UI", "0"),
            },
        )
    run_engine_hosted_app()


if __name__ == "__main__":
    main()

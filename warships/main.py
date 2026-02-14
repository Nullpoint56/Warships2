"""Application entry point."""

import logging
import os

from warships.app.loop import AppLoop
from warships.infra.config import load_env_file
from warships.infra.logging import setup_logging

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
    app = AppLoop()
    app.run()


if __name__ == "__main__":
    main()

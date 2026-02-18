"""Application entry point."""

import os

from warships.game.app.engine_hosted_runtime import run_engine_hosted_app
from engine.api.logging import get_logger
from warships.game.infra.app_data import apply_runtime_path_defaults
from warships.game.infra.config import load_default_env_files
from warships.game.infra.logging import setup_logging

logger = get_logger(__name__)


def main() -> None:
    """Run the Warships application."""
    load_default_env_files()
    paths = apply_runtime_path_defaults()
    setup_logging()
    logger.info(
        "app_data_paths root=%s logs=%s presets=%s saves=%s",
        paths["root"],
        paths["logs"],
        paths["presets"],
        paths["saves"],
    )
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

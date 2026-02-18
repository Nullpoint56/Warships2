from __future__ import annotations

import logging

from engine.runtime.logging import setup_engine_logging


def test_setup_engine_logging_adds_handler_when_missing(monkeypatch) -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    try:
        root.handlers.clear()
        root.setLevel(logging.NOTSET)
        monkeypatch.setenv("ENGINE_LOG_LEVEL", "DEBUG")
        setup_engine_logging()
        assert root.handlers
        assert root.level == logging.DEBUG
    finally:
        root.handlers.clear()
        root.handlers.extend(original_handlers)
        root.setLevel(original_level)


def test_setup_engine_logging_does_not_override_existing_handlers() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    sentinel = logging.NullHandler()
    try:
        root.handlers.clear()
        root.addHandler(sentinel)
        root.setLevel(logging.WARNING)
        setup_engine_logging()
        assert root.handlers == [sentinel]
        assert root.level == logging.WARNING
    finally:
        root.handlers.clear()
        root.handlers.extend(original_handlers)
        root.setLevel(original_level)


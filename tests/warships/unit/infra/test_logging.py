import logging
import os

from warships.game.infra.logging import JsonFormatter, setup_logging


def test_json_formatter_includes_fields_and_message() -> None:
    logger = logging.getLogger("test.json.formatter")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
        extra={"custom": 1},
    )
    payload = JsonFormatter().format(record)
    assert '"msg": "hello world"' in payload
    assert '"custom": 1' in payload


def test_setup_logging_text_and_json(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "text")
    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert root.handlers
    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()
    assert root.handlers

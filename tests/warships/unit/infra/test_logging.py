import logging
from pathlib import Path

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
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(Path.cwd() / "tmp_appdata"))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "text")
    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert root.handlers
    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()
    assert root.handlers


def test_setup_logging_writes_under_app_data_logs(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(tmp_path / "appdata"))
    monkeypatch.delenv("WARSHIPS_LOG_DIR", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")
    setup_logging()

    logger = logging.getLogger("test.logging.file.path")
    logger.info("hello")
    setup_logging()

    files = list((tmp_path / "appdata" / "logs").glob("warships_run_*.jsonl"))
    assert files

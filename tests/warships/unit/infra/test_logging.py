import logging
from pathlib import Path

from engine.runtime.logging import configure_engine_logging
from warships.game.infra.logging import JsonFormatter, build_logging_config


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


def test_build_logging_config_text_and_json(monkeypatch) -> None:
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(Path.cwd() / "tmp_appdata"))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "text")
    configure_engine_logging(build_logging_config())
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert root.handlers
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_engine_logging(build_logging_config())
    assert root.handlers


def test_build_logging_config_writes_under_app_data_logs(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(tmp_path / "appdata"))
    monkeypatch.delenv("WARSHIPS_LOG_DIR", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_engine_logging(build_logging_config())

    logger = logging.getLogger("test.logging.file.path")
    logger.info("hello")
    configure_engine_logging(build_logging_config())

    files = list((tmp_path / "appdata" / "logs").glob("warships_run_*.jsonl"))
    assert files

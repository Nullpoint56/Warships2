from __future__ import annotations

import os

from warships.game.infra.config import load_default_env_files, load_env_file


def test_load_env_file_sets_values_with_overwrite_by_default(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "A=1\nB='two'\n#comment\nINVALID\nC=three\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("C", "already")
    load_env_file(str(env_file))
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "two"
    assert os.environ.get("C") == "three"


def test_load_env_file_can_preserve_existing_values(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("C=three\n", encoding="utf-8")
    monkeypatch.setenv("C", "already")
    load_env_file(str(env_file), override_existing=False)
    assert os.environ.get("C") == "already"


def test_load_env_file_missing_is_noop(tmp_path) -> None:
    missing = tmp_path / ".env.missing"
    load_env_file(str(missing))
    assert True


def test_load_default_env_files_honors_order(tmp_path, monkeypatch) -> None:
    engine_env = tmp_path / ".env.engine"
    engine_local_env = tmp_path / ".env.engine.local"
    app_env = tmp_path / ".env.app"
    app_local_env = tmp_path / ".env.app.local"
    engine_env.write_text("A=engine\nB=engine\n", encoding="utf-8")
    engine_local_env.write_text("B=engine_local\n", encoding="utf-8")
    app_env.write_text("B=app\nC=app\n", encoding="utf-8")
    app_local_env.write_text("C=app_local\n", encoding="utf-8")

    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)

    load_default_env_files(
        paths=(
            str(engine_env),
            str(engine_local_env),
            str(app_env),
            str(app_local_env),
        )
    )
    assert os.environ.get("A") == "engine"
    assert os.environ.get("B") == "app"
    assert os.environ.get("C") == "app_local"

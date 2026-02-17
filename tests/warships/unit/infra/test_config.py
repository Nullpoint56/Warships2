from __future__ import annotations

import os

from warships.game.infra.config import load_env_file


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

from __future__ import annotations

from pathlib import Path

from warships.game.infra.app_data import (
    apply_runtime_path_defaults,
    resolve_app_data_root,
)


def test_resolve_app_data_root_prefers_configured_dir(monkeypatch, tmp_path) -> None:
    custom = tmp_path / "custom_root"
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(custom))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert resolve_app_data_root() == custom


def test_apply_runtime_path_defaults_sets_unified_paths(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(tmp_path / "warships_data"))
    monkeypatch.delenv("WARSHIPS_LOG_DIR", raising=False)
    monkeypatch.delenv("WARSHIPS_PRESETS_DIR", raising=False)

    paths = apply_runtime_path_defaults()

    assert Path(paths["logs"]).exists()
    assert Path(paths["presets"]).exists()
    assert Path(paths["saves"]).exists()
    assert Path(paths["logs"]).name == "logs"
    assert Path(paths["presets"]).name == "presets"
    assert Path(paths["saves"]).name == "saves"


def test_apply_runtime_path_defaults_normalizes_relative_env_paths(monkeypatch, tmp_path) -> None:
    root = tmp_path / "appdata_root"
    monkeypatch.setenv("WARSHIPS_APP_DATA_DIR", str(root))
    monkeypatch.setenv("WARSHIPS_LOG_DIR", "logs")
    monkeypatch.setenv("WARSHIPS_PRESETS_DIR", "presets")

    paths = apply_runtime_path_defaults()

    assert Path(paths["logs"]) == root / "logs"
    assert Path(paths["presets"]) == root / "presets"
    assert Path(paths["logs"]).exists()
    assert Path(paths["presets"]).exists()


def test_resolve_app_data_root_defaults_to_game_root_appdata(monkeypatch) -> None:
    monkeypatch.delenv("WARSHIPS_APP_DATA_DIR", raising=False)
    root = resolve_app_data_root()
    assert root.name == "appdata"
    assert root.parent.name == "warships"

from __future__ import annotations

from engine.diagnostics.config import load_diagnostics_config


def test_diagnostics_config_uses_runtime_profile_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_RUNTIME_PROFILE", "dev-fast")
    monkeypatch.delenv("ENGINE_DIAGNOSTICS_DEFAULT_SAMPLING_N", raising=False)
    monkeypatch.delenv("ENGINE_DIAGNOSTICS_CATEGORY_ALLOWLIST", raising=False)
    monkeypatch.delenv("ENGINE_DIAGNOSTICS_CATEGORY_SAMPLING", raising=False)

    cfg = load_diagnostics_config()
    assert cfg.event_default_sampling_n == 4
    assert "render" in cfg.event_category_allowlist
    assert cfg.event_category_sampling.get("render") == 2


def test_diagnostics_config_explicit_overrides_profile(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_RUNTIME_PROFILE", "release-like")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_DEFAULT_SAMPLING_N", "3")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_CATEGORY_ALLOWLIST", "frame,error")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_CATEGORY_SAMPLING", "frame:5,error:1")

    cfg = load_diagnostics_config()
    assert cfg.event_default_sampling_n == 3
    assert cfg.event_category_allowlist == ("frame", "error")
    assert cfg.event_category_sampling == {"frame": 5, "error": 1}

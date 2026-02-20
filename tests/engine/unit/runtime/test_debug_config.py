from __future__ import annotations

from engine.runtime.debug_config import (
    enabled_metrics,
    enabled_overlay,
    enabled_profiling,
    load_debug_config,
    resolve_log_level_name,
)


def test_load_debug_config_parses_flags_and_sampling(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_UI_OVERLAY_ENABLED", "true")
    monkeypatch.setenv("ENGINE_PROFILING_ENABLED", "1")
    monkeypatch.setenv("ENGINE_PROFILING_SAMPLING_N", "5")
    monkeypatch.setenv("ENGINE_LOG_LEVEL", "debug")

    cfg = load_debug_config()
    assert cfg.metrics_enabled is True
    assert cfg.overlay_enabled is True
    assert cfg.profiling_enabled is True
    assert cfg.profiling_sampling_n == 5
    assert cfg.log_level == "DEBUG"


def test_load_debug_config_profiling_sampling_is_clamped(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_PROFILING_SAMPLING_N", "0")
    cfg = load_debug_config()
    assert cfg.profiling_sampling_n == 1


def test_resolve_log_level_prefers_engine_prefix(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ENGINE_LOG_LEVEL", "ERROR")
    assert resolve_log_level_name() == "ERROR"


def test_enabled_helpers_read_current_env(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_UI_OVERLAY_ENABLED", "0")
    monkeypatch.setenv("ENGINE_PROFILING_ENABLED", "1")
    assert enabled_metrics() is True
    assert enabled_overlay() is False
    assert enabled_profiling() is True


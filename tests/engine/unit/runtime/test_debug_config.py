from __future__ import annotations

from engine.runtime.debug_config import (
    enabled_metrics,
    enabled_overlay,
    enabled_resize_trace,
    enabled_ui_trace,
    load_debug_config,
    resolve_log_level_name,
)


def test_load_debug_config_parses_flags_and_sampling(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DEBUG_OVERLAY", "true")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE", "yes")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_TRACE", "on")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_SAMPLING_N", "25")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_AUTO_DUMP", "0")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_DUMP_DIR", "diag_logs")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_PRIMITIVES", "1")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_KEY_FILTER", "board:,ship:,button:")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_LOG_EVERY_FRAME", "true")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_FORCE_INVALIDATE", "1")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SIZE_SOURCE_MODE", "event_only")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SIZE_QUANTIZATION", "round")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_CAMERA_SET_VIEW_SIZE", "true")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_SYNC_FROM_PHYSICAL_SIZE", "1")
    monkeypatch.setenv("ENGINE_DEBUG_RENDERER_FORCE_PIXEL_RATIO", "1.0")
    monkeypatch.setenv("ENGINE_LOG_LEVEL", "debug")

    cfg = load_debug_config()
    assert cfg.metrics_enabled is True
    assert cfg.overlay_enabled is True
    assert cfg.ui_trace_enabled is True
    assert cfg.resize_trace_enabled is True
    assert cfg.ui_trace_sampling_n == 25
    assert cfg.ui_trace_auto_dump is False
    assert cfg.ui_trace_dump_dir == "diag_logs"
    assert cfg.ui_trace_primitives_enabled is True
    assert cfg.ui_trace_key_filter == ("board:", "ship:", "button:")
    assert cfg.ui_trace_log_every_frame is True
    assert cfg.resize_force_invalidate is True
    assert cfg.resize_size_source_mode == "event_only"
    assert cfg.resize_size_quantization == "round"
    assert cfg.resize_camera_set_view_size is True
    assert cfg.resize_sync_from_physical_size is True
    assert cfg.renderer_force_pixel_ratio == 1.0
    assert cfg.log_level == "DEBUG"


def test_load_debug_config_sampling_is_clamped(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE_SAMPLING_N", "0")
    cfg = load_debug_config()
    assert cfg.ui_trace_sampling_n == 1


def test_resolve_log_level_prefers_engine_prefix(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ENGINE_LOG_LEVEL", "ERROR")
    assert resolve_log_level_name() == "ERROR"


def test_enabled_helpers_read_current_env(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DEBUG_METRICS", "1")
    monkeypatch.setenv("ENGINE_DEBUG_OVERLAY", "0")
    monkeypatch.setenv("ENGINE_DEBUG_UI_TRACE", "1")
    monkeypatch.setenv("ENGINE_DEBUG_RESIZE_TRACE", "0")
    assert enabled_metrics() is True
    assert enabled_overlay() is False
    assert enabled_ui_trace() is True
    assert enabled_resize_trace() is False

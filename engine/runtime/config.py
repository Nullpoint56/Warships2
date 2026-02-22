"""Centralized runtime configuration ownership for engine execution."""

from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Mapping

from engine.runtime_profile import (
    RuntimeProfile,
    RuntimeProfileName,
    normalize_runtime_profile_name,
    resolve_runtime_profile,
)


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapConfig:
    headless: bool
    wgpu_backends: tuple[str, ...]
    panel_width: int
    panel_height: int


@dataclass(frozen=True, slots=True)
class RuntimeRenderConfig:
    vsync: bool
    loop_mode: str
    fps_cap: float
    preserve_aspect: bool
    window_mode: str
    ui_resolution: tuple[int, int] | None
    ui_design_width: int
    ui_design_height: int


@dataclass(frozen=True, slots=True)
class RuntimeWindowConfig:
    backend: str
    events_trace_enabled: bool
    resize_redraw_min_interval_ms: float


@dataclass(frozen=True, slots=True)
class RuntimeHostConfig:
    profile_log_payload_enabled: bool
    diagnostics_http_enabled: bool
    diagnostics_http_host: str
    diagnostics_http_port: int
    replay_seed: str | None
    render_snapshot_sanitize: bool


@dataclass(frozen=True, slots=True)
class RuntimeInputConfig:
    trace_enabled: bool


@dataclass(frozen=True, slots=True)
class RuntimeStyleConfig:
    effects_enabled: bool


@dataclass(frozen=True, slots=True)
class RuntimeDiagnosticsAdapterConfig:
    emit_system_timings: bool
    emit_event_topic_breakdown: bool


@dataclass(frozen=True, slots=True)
class RuntimeProfilingConfig:
    include_system_timings: bool
    include_event_topics: bool
    system_top_n: int
    capture_enabled: bool
    capture_frames: int
    capture_top_n: int
    capture_sort: str
    capture_export_dir: str
    capture_tracemalloc_depth: int
    capture_timeline_max: int
    capture_warmup_frames: int


@dataclass(frozen=True, slots=True)
class RuntimeRendererConfig:
    present_modes: tuple[str, ...]
    diag_stage_events_enabled: bool
    diag_stage_sampling_n: int
    diag_profile_sampling_n: int
    auto_static_min_stable_frames: int
    internal_scale: float
    cffi_miss_diagnostics_enabled: bool
    cffi_fastpath_enabled: bool
    cffi_fastpath_cache_max: int
    cffi_prewarm_enabled: bool
    cffi_prewarm_max_types: int
    cffi_prewarm_max_literals: int
    recovery_failure_streak_threshold: int
    recovery_cooldown_ms: float
    recovery_max_retry_limit: int
    static_bundle_min_draws: int
    static_pass_expand_cache_max: int
    prime_native_paths: bool
    text_prewarm_enabled: bool
    text_prewarm_sizes: tuple[int, ...]
    text_prewarm_chars: str
    text_prewarm_labels: tuple[str, ...]
    text_prewarm_max_chars: int
    startup_prewarm_enabled: bool
    startup_prewarm_frames: int
    font_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    profile_name: RuntimeProfileName
    profile: RuntimeProfile
    bootstrap: RuntimeBootstrapConfig
    render: RuntimeRenderConfig
    window: RuntimeWindowConfig
    host: RuntimeHostConfig
    input: RuntimeInputConfig
    style: RuntimeStyleConfig
    diagnostics_adapter: RuntimeDiagnosticsAdapterConfig
    profiling: RuntimeProfilingConfig
    renderer: RuntimeRendererConfig


_RUNTIME_CONFIG: ContextVar[RuntimeConfig | None] = ContextVar("engine_runtime_config", default=None)


def _raw(name: str, *, env: Mapping[str, str] | None = None) -> str | None:
    value = os.getenv(name) if env is None else env.get(name)
    return None if value is None else str(value)


def _flag(name: str, default: bool, *, env: Mapping[str, str] | None = None) -> bool:
    raw = _raw(name, env=env)
    if raw is None:
        return bool(default)
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    raw = _raw(name, env=env)
    if raw is None:
        value = int(default)
    else:
        try:
            value = int(raw.strip())
        except ValueError:
            value = int(default)
    if minimum is None:
        return value
    return max(int(minimum), value)


def _float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    env: Mapping[str, str] | None = None,
) -> float:
    raw = _raw(name, env=env)
    if raw is None:
        value = float(default)
    else:
        try:
            value = float(raw.strip())
        except ValueError:
            value = float(default)
    if minimum is None:
        return value
    return max(float(minimum), value)


def _text(name: str, default: str, *, env: Mapping[str, str] | None = None) -> str:
    raw = _raw(name, env=env)
    if raw is None:
        return str(default)
    value = raw.strip()
    return value if value else str(default)


def _csv(name: str, *, env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    raw = _text(name, "", env=env)
    if not raw:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _resolution(raw: str) -> tuple[int, int] | None:
    value = str(raw).strip().lower()
    if not value:
        return None
    normalized = value.replace(" ", "")
    for sep in ("x", ",", ":"):
        if sep in normalized:
            left, right = normalized.split(sep, 1)
            try:
                width = max(1, int(left))
                height = max(1, int(right))
            except ValueError:
                return None
            return (width, height)
    return None


def _normalize_window_backend(raw: str) -> str:
    value = str(raw).strip().lower()
    if value in {"rendercanvas", "rendercanvas_glfw", "glfw"}:
        return "rendercanvas_glfw"
    if value in {"direct_glfw", "glfw_direct"}:
        return "direct_glfw"
    return value


def _normalize_loop_mode(raw: str, fallback: str) -> str:
    value = str(raw).strip().lower()
    if value not in {"on_demand", "continuous"}:
        return str(fallback)
    return value


def load_runtime_config(*, env: Mapping[str, str] | None = None) -> RuntimeConfig:
    scope_env = env
    profile_name = normalize_runtime_profile_name(_raw("ENGINE_RUNTIME_PROFILE", env=scope_env))
    profile = resolve_runtime_profile(profile_name=profile_name)

    ui_resolution = _resolution(_text("ENGINE_UI_RESOLUTION", "", env=scope_env))
    panel_resolution = _resolution(_text("ENGINE_UI_PANEL_RESOLUTION", "", env=scope_env))
    panel_width = int(panel_resolution[0]) if panel_resolution is not None else 1280
    panel_height = int(panel_resolution[1]) if panel_resolution is not None else 800

    wgpu_backends_csv = _csv("ENGINE_WGPU_BACKENDS", env=scope_env)
    wgpu_backends = (
        tuple(item.lower() for item in wgpu_backends_csv)
        if wgpu_backends_csv
        else ("vulkan", "metal", "dx12")
    )

    present_modes_csv = _csv("ENGINE_WGPU_PRESENT_MODES", env=scope_env)
    present_modes = (
        tuple(item.lower() for item in present_modes_csv)
        if present_modes_csv
        else ("fifo", "mailbox", "immediate")
    )

    raw_chars = _text(
        "ENGINE_WGPU_TEXT_PREWARM_CHARS",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,:;!?-_()/[]{}+#",
        env=scope_env,
    )
    text_prewarm_labels = tuple(
        item.strip()
        for item in _text(
            "ENGINE_WGPU_TEXT_PREWARM_LABELS",
            "New Game|Resume|Options|Back|Start|Preset|Difficulty|Random Fleet|Generate Random Fleet",
            env=scope_env,
        ).split("|")
        if item.strip()
    )
    text_prewarm_sizes_raw = _csv("ENGINE_WGPU_TEXT_PREWARM_SIZES", env=scope_env)
    text_prewarm_sizes: list[int] = []
    for item in text_prewarm_sizes_raw:
        try:
            text_prewarm_sizes.append(max(6, int(item)))
        except ValueError:
            continue
    if not text_prewarm_sizes:
        text_prewarm_sizes = [14, 18, 24]

    font_paths_raw = _text("ENGINE_WGPU_FONT_PATHS", "", env=scope_env).strip()
    font_paths: tuple[str, ...]
    if font_paths_raw:
        sep = ";" if ";" in font_paths_raw else os.pathsep
        font_paths = tuple(item.strip() for item in font_paths_raw.split(sep) if item.strip())
    else:
        font_paths = ()

    diagnostics_http_port = _int("ENGINE_DIAGNOSTICS_HTTP_PORT", 8765, env=scope_env)
    diagnostics_http_host = _text("ENGINE_DIAGNOSTICS_HTTP_HOST", "127.0.0.1", env=scope_env)
    replay_seed = _text("ENGINE_REPLAY_SEED", "", env=scope_env).strip()
    if not replay_seed:
        replay_seed = _text("WARSHIPS_RNG_SEED", "", env=scope_env).strip()
    replay_seed_value = replay_seed if replay_seed else None

    return RuntimeConfig(
        profile_name=profile_name,
        profile=profile,
        bootstrap=RuntimeBootstrapConfig(
            headless=_flag("ENGINE_HEADLESS", False, env=scope_env),
            wgpu_backends=wgpu_backends,
            panel_width=max(1, int(panel_width)),
            panel_height=max(1, int(panel_height)),
        ),
        render=RuntimeRenderConfig(
            vsync=_flag("ENGINE_RENDER_VSYNC", profile.render_vsync, env=scope_env),
            loop_mode=_normalize_loop_mode(
                _text("ENGINE_RENDER_LOOP_MODE", profile.render_loop_mode, env=scope_env),
                profile.render_loop_mode,
            ),
            fps_cap=max(0.0, _float("ENGINE_RENDER_FPS_CAP", profile.render_fps_cap, env=scope_env)),
            preserve_aspect=_text("ENGINE_UI_ASPECT_MODE", "stretch", env=scope_env).lower()
            in {"contain", "preserve", "fixed"},
            window_mode=_text("ENGINE_WINDOW_MODE", "windowed", env=scope_env).lower(),
            ui_resolution=ui_resolution,
            ui_design_width=_int("ENGINE_UI_DESIGN_WIDTH", 1200, minimum=1, env=scope_env),
            ui_design_height=_int("ENGINE_UI_DESIGN_HEIGHT", 720, minimum=1, env=scope_env),
        ),
        window=RuntimeWindowConfig(
            backend=_normalize_window_backend(_text("ENGINE_WINDOW_BACKEND", "rendercanvas_glfw", env=scope_env)),
            events_trace_enabled=_flag("ENGINE_WINDOW_EVENTS_TRACE_ENABLED", False, env=scope_env),
            resize_redraw_min_interval_ms=_float(
                "ENGINE_WINDOW_RESIZE_REDRAW_MIN_INTERVAL_MS", 16.0, minimum=0.0, env=scope_env
            ),
        ),
        host=RuntimeHostConfig(
            profile_log_payload_enabled=_flag(
                "ENGINE_PROFILING_LOG_PAYLOAD_ENABLED", True, env=scope_env
            ),
            diagnostics_http_enabled=_flag("ENGINE_DIAGNOSTICS_HTTP_ENABLED", True, env=scope_env),
            diagnostics_http_host=diagnostics_http_host or "127.0.0.1",
            diagnostics_http_port=max(1, int(diagnostics_http_port)),
            replay_seed=replay_seed_value,
            render_snapshot_sanitize=_flag(
                "ENGINE_RUNTIME_RENDER_SNAPSHOT_SANITIZE", True, env=scope_env
            ),
        ),
        input=RuntimeInputConfig(
            trace_enabled=_flag("ENGINE_INPUT_TRACE_ENABLED", False, env=scope_env),
        ),
        style=RuntimeStyleConfig(
            effects_enabled=_flag("ENGINE_UI_STYLE_EFFECTS", True, env=scope_env),
        ),
        diagnostics_adapter=RuntimeDiagnosticsAdapterConfig(
            emit_system_timings=_flag("ENGINE_DIAGNOSTICS_EMIT_SYSTEM_TIMINGS", False, env=scope_env),
            emit_event_topic_breakdown=_flag(
                "ENGINE_DIAGNOSTICS_EMIT_EVENT_TOPIC_BREAKDOWN", False, env=scope_env
            ),
        ),
        profiling=RuntimeProfilingConfig(
            include_system_timings=_flag(
                "ENGINE_PROFILING_INCLUDE_SYSTEM_TIMINGS", False, env=scope_env
            ),
            include_event_topics=_flag("ENGINE_PROFILING_INCLUDE_EVENT_TOPICS", False, env=scope_env),
            system_top_n=_int("ENGINE_PROFILING_SYSTEM_TOP_N", 5, minimum=1, env=scope_env),
            capture_enabled=_flag("ENGINE_PROFILING_CAPTURE_ENABLED", False, env=scope_env),
            capture_frames=_int("ENGINE_PROFILING_CAPTURE_FRAMES", 180, minimum=1, env=scope_env),
            capture_top_n=_int("ENGINE_PROFILING_CAPTURE_TOP_N", 80, minimum=10, env=scope_env),
            capture_sort=_text("ENGINE_PROFILING_CAPTURE_SORT", "cumtime", env=scope_env).lower(),
            capture_export_dir=_text(
                "ENGINE_PROFILING_CAPTURE_EXPORT_DIR", "tools/data/profiles", env=scope_env
            ),
            capture_tracemalloc_depth=_int(
                "ENGINE_PROFILING_CAPTURE_TRACEMALLOC_DEPTH", 25, minimum=1, env=scope_env
            ),
            capture_timeline_max=_int(
                "ENGINE_PROFILING_CAPTURE_TIMELINE_MAX", 600, minimum=60, env=scope_env
            ),
            capture_warmup_frames=_int(
                "ENGINE_PROFILING_CAPTURE_WARMUP_FRAMES", 30, minimum=10, env=scope_env
            ),
        ),
        renderer=RuntimeRendererConfig(
            present_modes=present_modes,
            diag_stage_events_enabled=_flag(
                "ENGINE_DIAGNOSTICS_RENDER_STAGE_EVENTS_ENABLED", True, env=scope_env
            ),
            diag_stage_sampling_n=_int(
                "ENGINE_DIAGNOSTICS_RENDER_STAGE_SAMPLING_N",
                profile.diagnostics_default_sampling_n,
                minimum=1,
                env=scope_env,
            ),
            diag_profile_sampling_n=_int(
                "ENGINE_DIAGNOSTICS_RENDER_PROFILE_SAMPLING_N",
                profile.diagnostics_default_sampling_n,
                minimum=1,
                env=scope_env,
            ),
            auto_static_min_stable_frames=_int(
                "ENGINE_RENDER_AUTO_STATIC_MIN_STABLE_FRAMES", 3, minimum=1, env=scope_env
            ),
            internal_scale=_float("ENGINE_RENDER_INTERNAL_SCALE", 1.0, minimum=0.1, env=scope_env),
            cffi_miss_diagnostics_enabled=_flag(
                "ENGINE_WGPU_CFFI_MISS_DIAGNOSTICS_ENABLED", False, env=scope_env
            ),
            cffi_fastpath_enabled=_flag(
                "ENGINE_WGPU_CFFI_FASTPATH_ENABLED", True, env=scope_env
            ),
            cffi_fastpath_cache_max=_int(
                "ENGINE_WGPU_CFFI_FASTPATH_CACHE_MAX", 512, minimum=64, env=scope_env
            ),
            cffi_prewarm_enabled=_flag(
                "ENGINE_WGPU_CFFI_PREWARM_ENABLED", True, env=scope_env
            ),
            cffi_prewarm_max_types=_int(
                "ENGINE_WGPU_CFFI_PREWARM_MAX_TYPES", 256, minimum=32, env=scope_env
            ),
            cffi_prewarm_max_literals=_int(
                "ENGINE_WGPU_CFFI_PREWARM_MAX_LITERALS", 2048, minimum=128, env=scope_env
            ),
            recovery_failure_streak_threshold=_int(
                "ENGINE_WGPU_RECOVERY_FAILURE_STREAK_THRESHOLD", 3, minimum=1, env=scope_env
            ),
            recovery_cooldown_ms=_float(
                "ENGINE_WGPU_RECOVERY_COOLDOWN_MS", 50.0, minimum=0.0, env=scope_env
            ),
            recovery_max_retry_limit=_int(
                "ENGINE_WGPU_RECOVERY_MAX_RETRY_LIMIT", 4, minimum=2, env=scope_env
            ),
            static_bundle_min_draws=_int(
                "ENGINE_RENDER_STATIC_BUNDLE_MIN_DRAWS", 2, minimum=1, env=scope_env
            ),
            static_pass_expand_cache_max=_int(
                "ENGINE_RENDER_STATIC_PASS_EXPAND_CACHE_MAX", 512, minimum=64, env=scope_env
            ),
            prime_native_paths=_flag("ENGINE_WGPU_PRIME_NATIVE_PATHS", True, env=scope_env),
            text_prewarm_enabled=_flag("ENGINE_WGPU_TEXT_PREWARM_ENABLED", False, env=scope_env),
            text_prewarm_sizes=tuple(text_prewarm_sizes),
            text_prewarm_chars=raw_chars,
            text_prewarm_labels=text_prewarm_labels,
            text_prewarm_max_chars=_int(
                "ENGINE_WGPU_TEXT_PREWARM_MAX_CHARS", 96, minimum=8, env=scope_env
            ),
            startup_prewarm_enabled=_flag(
                "ENGINE_WGPU_STARTUP_PREWARM_ENABLED", False, env=scope_env
            ),
            startup_prewarm_frames=_int(
                "ENGINE_WGPU_STARTUP_PREWARM_FRAMES", 1, minimum=1, env=scope_env
            ),
            font_paths=font_paths,
        ),
    )


def initialize_runtime_config(*, env: Mapping[str, str] | None = None) -> RuntimeConfig:
    config = load_runtime_config(env=env)
    _RUNTIME_CONFIG.set(config)
    return config


def set_runtime_config(config: RuntimeConfig) -> RuntimeConfig:
    _RUNTIME_CONFIG.set(config)
    return config


def get_runtime_config() -> RuntimeConfig:
    config = _RUNTIME_CONFIG.get()
    if config is not None:
        return config
    return initialize_runtime_config()


__all__ = [
    "RuntimeBootstrapConfig",
    "RuntimeConfig",
    "RuntimeDiagnosticsAdapterConfig",
    "RuntimeHostConfig",
    "RuntimeInputConfig",
    "RuntimeProfilingConfig",
    "RuntimeRenderConfig",
    "RuntimeRendererConfig",
    "RuntimeStyleConfig",
    "RuntimeWindowConfig",
    "get_runtime_config",
    "initialize_runtime_config",
    "load_runtime_config",
    "set_runtime_config",
]

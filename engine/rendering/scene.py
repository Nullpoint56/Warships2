"""Scene graph setup for pygfx rendering."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

from engine.diagnostics.hub import DiagnosticHub
from engine.rendering.scene_retained import (
    hide_inactive_nodes,
    upsert_grid,
    upsert_rect,
    upsert_text,
)
from engine.rendering.scene_runtime import (
    get_canvas_logical_size,
    resolve_preserve_aspect,
    resolve_render_loop_config,
    resolve_render_vsync,
    run_backend_loop,
    stop_backend_loop,
)
from engine.rendering.scene_viewport import (
    extract_resize_dimensions,
    to_design_space,
    viewport_transform,
)
from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.rendering.ui_diagnostics import UIDiagnostics, UIDiagnosticsConfig
from engine.runtime.debug_config import load_debug_config

_gfx_import_error: Exception | None
try:
    import pygfx as gfx
except Exception as exc:  # pragma: no cover - import guard for environments without graphics deps
    gfx = None
    _gfx_import_error = exc
else:
    _gfx_import_error = None

_canvas_import_error: Exception | None
try:
    import rendercanvas.auto as rc_auto
except Exception as exc:  # pragma: no cover - missing GUI backend
    rc_auto = None
    _canvas_import_error = exc
else:
    _canvas_import_error = None
    try:
        # Guard against transient zero-size events (e.g. snap/resize on Windows) before they
        # propagate into rendercanvas internals.
        from rendercanvas import _size as _rc_size

        if not getattr(_rc_size.SizeInfo.set_physical_size, "_engine_size_clamped", False):
            _orig_set_physical_size = _rc_size.SizeInfo.set_physical_size

            def _safe_set_physical_size(
                self: object, width: int, height: int, pixel_ratio: float
            ) -> None:
                _orig_set_physical_size(self, max(1, int(width)), max(1, int(height)), pixel_ratio)

            marker_target = cast(Any, _safe_set_physical_size)
            marker_target._engine_size_clamped = True
            _rc_size.SizeInfo.set_physical_size = _safe_set_physical_size
    except Exception:
        pass

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from engine.diagnostics.hub import DiagnosticHub


@dataclass(frozen=True, slots=True)
class _RenderPassBatch:
    """Prepared pass batch ready for deterministic execution."""

    name: str
    commands: tuple[RenderCommand, ...]


@dataclass(frozen=True, slots=True)
class _PassDescriptor:
    """Canonical pass descriptor used for ordering and diagnostics."""

    canonical_name: str
    priority: int


@dataclass(slots=True)
class SceneRenderer:
    """Minimal 2D renderer wrapper around pygfx."""

    width: int = 1200
    height: int = 720
    design_width: int = 1200
    design_height: int = 720
    preserve_aspect: bool = False
    title: str = "Engine Runtime"
    _dynamic_nodes: list[object] = field(default_factory=list)
    _rect_nodes: dict[str, Any] = field(default_factory=dict)
    _line_nodes: dict[str, Any] = field(default_factory=dict)
    _text_nodes: dict[str, Any] = field(default_factory=dict)
    _rect_props: dict[str, tuple[float, float, float, float, str, float]] = field(
        default_factory=dict
    )
    _line_props: dict[str, tuple[float, float, float, float, int, str, float]] = field(
        default_factory=dict
    )
    _text_props: dict[str, tuple[str, float, float, float, str, str, float]] = field(
        default_factory=dict
    )
    _rect_viewport_rev: dict[str, int] = field(default_factory=dict)
    _line_viewport_rev: dict[str, int] = field(default_factory=dict)
    _text_viewport_rev: dict[str, int] = field(default_factory=dict)
    _rect_transformed_props: dict[str, tuple[float, float, float, float]] = field(
        default_factory=dict
    )
    _line_transformed_props: dict[str, tuple[float, float, float, float]] = field(
        default_factory=dict
    )
    _text_transformed_props: dict[str, tuple[float, float, float, float]] = field(
        default_factory=dict
    )
    _static_rect_keys: set[str] = field(default_factory=set)
    _static_line_keys: set[str] = field(default_factory=set)
    _static_text_keys: set[str] = field(default_factory=set)
    _active_rect_keys: set[str] = field(default_factory=set)
    _active_line_keys: set[str] = field(default_factory=set)
    _active_text_keys: set[str] = field(default_factory=set)
    canvas: Any | None = None
    renderer: Any = field(init=False)
    scene: Any = field(init=False)
    camera: Any = field(init=False)
    _draw_failed: bool = field(init=False, default=False)
    _is_closed: bool = field(init=False, default=False)
    _draw_callback: Callable[[], None] | None = field(init=False, default=None)
    _viewport_revision: int = field(init=False, default=0)
    _ui_diagnostics: UIDiagnostics | None = field(init=False, default=None)
    _frame_active: bool = field(init=False, default=False)
    _frame_viewport: tuple[float, float, float, float] | None = field(init=False, default=None)
    _frame_viewport_revision: int | None = field(init=False, default=None)
    _frame_window_size: tuple[float, float] | None = field(init=False, default=None)
    _runtime_info: dict[str, object] = field(init=False, default_factory=dict)
    _resize_force_invalidate: bool = field(init=False, default=False)
    _resize_size_source_mode: str = field(init=False, default="both")
    _resize_size_quantization: str = field(init=False, default="trunc")
    _resize_camera_set_view_size: bool = field(init=False, default=False)
    _resize_sync_from_physical_size: bool = field(init=False, default=False)
    _renderer_force_pixel_ratio: float = field(init=False, default=0.0)
    _render_loop_mode: str = field(init=False, default="on_demand")
    _render_fps_cap: float = field(init=False, default=60.0)
    _render_vsync: bool = field(init=False, default=True)
    _render_resize_cooldown_s: float = field(init=False, default=0.25)
    _resize_continuous_until: float = field(init=False, default=0.0)
    _next_continuous_frame_due: float = field(init=False, default=0.0)
    _diagnostics_hub: DiagnosticHub | None = field(init=False, default=None)
    _last_resize_applied_ts: float | None = field(init=False, default=None)
    _last_resize_event_to_apply_ms: float | None = field(init=False, default=None)
    _owns_canvas: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if gfx is None:
            raise RuntimeError(
                f"pygfx dependency unavailable: {_gfx_import_error!r}. Install 'pygfx' and 'wgpu'."
            )
        bootstrap_loop_cfg = resolve_render_loop_config()
        self._render_loop_mode = bootstrap_loop_cfg.mode
        self._render_fps_cap = bootstrap_loop_cfg.fps_cap
        self._render_resize_cooldown_s = max(
            0.0, float(bootstrap_loop_cfg.resize_cooldown_ms) / 1000.0
        )
        self._render_vsync = resolve_render_vsync()
        bootstrap_update_mode = (
            "continuous" if self._render_loop_mode == "continuous" else "ondemand"
        )
        bootstrap_max_fps = self._render_fps_cap if self._render_fps_cap > 0.0 else 240.0
        if self.canvas is None:
            if rc_auto is None:
                raise RuntimeError(
                    "Render canvas backend unavailable. "
                    "Install a desktop backend such as 'glfw' or 'pyside6'. "
                    f"Original error: {_canvas_import_error!r}"
                )

            canvas_cls = getattr(rc_auto, "RenderCanvas", None)
            if canvas_cls is None:
                raise RuntimeError("rendercanvas.auto did not expose RenderCanvas.")
            try:
                self.canvas = canvas_cls(
                    size=(self.width, self.height),
                    title=self.title,
                    update_mode=bootstrap_update_mode,
                    min_fps=0.0,
                    max_fps=float(bootstrap_max_fps),
                    vsync=self._render_vsync,
                )
            except TypeError:
                # Keep compatibility with simplified test/fallback canvas factories.
                self.canvas = canvas_cls(size=(self.width, self.height), title=self.title)
            self._owns_canvas = True
        else:
            self._owns_canvas = False
        if self.canvas is None:
            raise RuntimeError("renderer canvas initialization failed")
        self.preserve_aspect = resolve_preserve_aspect()
        self.renderer = gfx.WgpuRenderer(self.canvas)
        self.scene = gfx.Scene()
        self.camera = gfx.OrthographicCamera(self.width, self.height)
        self._configure_diagnostics()
        self._update_camera_projection()
        self._bind_resize_events()
        self._sync_size_from_canvas()

    def _configure_diagnostics(self) -> None:
        cfg = load_debug_config()
        self._resize_force_invalidate = cfg.resize_force_invalidate
        mode = cfg.resize_size_source_mode
        if mode not in {"both", "event_only", "poll_only"}:
            mode = "both"
        self._resize_size_source_mode = mode
        quant = cfg.resize_size_quantization
        if quant not in {"trunc", "round"}:
            quant = "trunc"
        self._resize_size_quantization = quant
        self._resize_camera_set_view_size = cfg.resize_camera_set_view_size
        self._resize_sync_from_physical_size = cfg.resize_sync_from_physical_size
        self._renderer_force_pixel_ratio = (
            float(cfg.renderer_force_pixel_ratio) if cfg.renderer_force_pixel_ratio > 0.0 else 0.0
        )
        render_loop_cfg = resolve_render_loop_config()
        self._render_loop_mode = render_loop_cfg.mode
        self._render_fps_cap = render_loop_cfg.fps_cap
        self._render_resize_cooldown_s = max(
            0.0, float(render_loop_cfg.resize_cooldown_ms) / 1000.0
        )
        self._render_vsync = resolve_render_vsync()
        self._apply_canvas_update_mode()
        self._apply_renderer_pixel_ratio_experiment()
        self._runtime_info = self._resolve_runtime_info()
        if not cfg.ui_trace_enabled and not cfg.resize_trace_enabled:
            self._ui_diagnostics = None
            return
        self._ui_diagnostics = UIDiagnostics(
            UIDiagnosticsConfig(
                ui_trace_enabled=cfg.ui_trace_enabled,
                resize_trace_enabled=cfg.resize_trace_enabled,
                sampling_n=cfg.ui_trace_sampling_n,
                auto_dump_on_anomaly=cfg.ui_trace_auto_dump,
                dump_dir=cfg.ui_trace_dump_dir,
                primitive_trace_enabled=cfg.ui_trace_primitives_enabled,
                trace_key_prefixes=cfg.ui_trace_key_filter,
                log_every_frame=cfg.ui_trace_log_every_frame,
            )
        )
        self._ui_diagnostics.set_runtime_info(self._runtime_info)

    def _apply_canvas_update_mode(self) -> None:
        set_update_mode = getattr(self.canvas, "set_update_mode", None)
        if not callable(set_update_mode):
            return
        # rendercanvas defaults max_fps to 30; always override it from runtime config.
        max_fps = self._render_fps_cap if self._render_fps_cap > 0.0 else 240.0
        update_mode = "continuous" if self._render_loop_mode == "continuous" else "ondemand"
        try:
            set_update_mode(update_mode, min_fps=0.0, max_fps=float(max_fps))
        except Exception:
            logger.debug("canvas_update_mode_apply_failed", exc_info=True)

    def _bind_resize_events(self) -> None:
        add_handler = getattr(self.canvas, "add_event_handler", None)
        if not callable(add_handler):
            return
        try:
            add_handler(self._on_resize, "resize")
        except Exception:
            logger.debug("resize_event_binding_failed", exc_info=True)

    def _on_resize(self, event: object) -> None:
        event_ts = perf_counter()
        if self._render_loop_mode == "continuous_during_resize":
            self._resize_continuous_until = event_ts + self._render_resize_cooldown_s
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_frame_reason("resize")
        if not isinstance(event, dict):
            self._sync_size_from_canvas()
            return
        width, height = extract_resize_dimensions(event)
        if width is None or height is None:
            self._sync_size_from_canvas()
            return
        if self._resize_size_source_mode != "poll_only":
            self._apply_canvas_size(width, height)
        size_applied_ts = perf_counter()
        event_to_apply_ms = (size_applied_ts - event_ts) * 1000.0
        self._last_resize_applied_ts = size_applied_ts
        self._last_resize_event_to_apply_ms = event_to_apply_ms
        hub = self._diagnostics_hub
        if hub is not None:
            hub.emit_fast(
                category="render",
                name="render.resize_event",
                tick=max(0, self._viewport_revision),
                value={"width": int(self.width), "height": int(self.height)},
                metadata={
                    "event_size": (float(width), float(height)),
                    "applied_size": (int(self.width), int(self.height)),
                    "viewport": self._viewport_transform(),
                    "event_to_apply_ms": event_to_apply_ms,
                },
            )
        if diagnostics is not None:
            size_payload = event.get("size")
            logical_size: tuple[float, float] | None = None
            if (
                isinstance(size_payload, (tuple, list))
                and len(size_payload) == 2
                and all(isinstance(v, (int, float)) for v in size_payload)
            ):
                logical_size = (float(size_payload[0]), float(size_payload[1]))
            physical_size: tuple[int, int] | None = None
            pixel_ratio = event.get("pixel_ratio")
            if (
                logical_size is not None
                and isinstance(pixel_ratio, (int, float))
                and pixel_ratio > 0
            ):
                physical_size = (
                    int(logical_size[0] * float(pixel_ratio)),
                    int(logical_size[1] * float(pixel_ratio)),
                )
            diagnostics.note_resize_event(
                event_size=(float(width), float(height)),
                logical_size=logical_size,
                physical_size=physical_size,
                applied_size=(self.width, self.height),
                viewport=self._viewport_transform(),
                event_ts=event_ts,
                size_applied_ts=size_applied_ts,
            )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                (
                    "resize_event event_size=(%.1f,%.1f) applied_size=(%d,%d) "
                    "viewport=(sx=%.4f,sy=%.4f,ox=%.2f,oy=%.2f)"
                ),
                float(width),
                float(height),
                self.width,
                self.height,
                self._viewport_transform()[0],
                self._viewport_transform()[1],
                self._viewport_transform()[2],
                self._viewport_transform()[3],
            )
        if self._resize_force_invalidate:
            self.invalidate()

    def _apply_canvas_size(self, width: float, height: float) -> bool:
        if width <= 1.0 or height <= 1.0:
            return False
        new_width = self._quantize_size(width)
        new_height = self._quantize_size(height)
        if new_width == self.width and new_height == self.height:
            return False
        self.width = new_width
        self.height = new_height
        self._viewport_revision += 1
        self._update_camera_projection()
        return True

    def _update_camera_projection(self) -> None:
        if self._resize_camera_set_view_size and hasattr(self.camera, "set_view_size"):
            try:
                self.camera.set_view_size(float(self.width), float(self.height))
            except Exception:
                logger.debug("camera_set_view_size_failed", exc_info=True)
        if hasattr(self.camera, "width"):
            self.camera.width = self.width
        if hasattr(self.camera, "height"):
            self.camera.height = self.height
        self.camera.local.position = (self.width / 2.0, self.height / 2.0, 0.0)
        self.camera.local.scale_y = -1.0
        self._emit_render_projection_events(reason="projection_update")

    def _emit_render_projection_events(self, *, reason: str) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        tick = max(0, self._viewport_revision)
        sx, sy, ox, oy = self._viewport_transform()
        hub.emit_fast(
            category="render",
            name="render.viewport_applied",
            tick=tick,
            value={
                "width": int(self.width),
                "height": int(self.height),
                "revision": int(self._viewport_revision),
                "sx": float(sx),
                "sy": float(sy),
                "ox": float(ox),
                "oy": float(oy),
            },
            metadata={"reason": reason},
        )
        hub.emit_fast(
            category="render",
            name="render.camera_projection",
            tick=tick,
            value={
                "camera_width": float(getattr(self.camera, "width", self.width)),
                "camera_height": float(getattr(self.camera, "height", self.height)),
                "camera_position": [
                    float(self.width / 2.0),
                    float(self.height / 2.0),
                    0.0,
                ],
                "camera_scale_y": float(getattr(self.camera.local, "scale_y", -1.0)),
            },
            metadata={"reason": reason},
        )
        canvas_ratio = self._get_canvas_pixel_ratio()
        renderer_ratio = getattr(self.renderer, "pixel_ratio", None)
        renderer_ratio_f = (
            float(renderer_ratio)
            if isinstance(renderer_ratio, (int, float)) and float(renderer_ratio) > 0.0
            else None
        )
        hub.emit_fast(
            category="render",
            name="render.pixel_ratio",
            tick=tick,
            value={
                "effective": float(self._effective_size_pixel_ratio()),
                "canvas": float(canvas_ratio) if canvas_ratio is not None else None,
                "renderer": renderer_ratio_f,
            },
            metadata={"reason": reason},
        )
        logical = get_canvas_logical_size(self.canvas)
        physical = self._get_canvas_physical_size()
        backend_state = self._collect_backend_state()
        renderer_sizes_obj = backend_state.get("renderer_sizes")
        renderer_sizes: dict[str, object] = {}
        if isinstance(renderer_sizes_obj, dict):
            renderer_sizes = {str(key): value for key, value in renderer_sizes_obj.items()}
        hub.emit_fast(
            category="render",
            name="render.surface_dims",
            tick=tick,
            value={
                "canvas_logical": [float(logical[0]), float(logical[1])] if logical else None,
                "canvas_physical": [float(physical[0]), float(physical[1])] if physical else None,
                "renderer_logical": renderer_sizes.get("logical_size"),
                "renderer_physical": renderer_sizes.get("physical_size"),
            },
            metadata={"reason": reason},
        )

    def _sync_size_from_canvas(self) -> bool:
        if self._resize_sync_from_physical_size:
            physical = self._get_canvas_physical_size()
            if physical is not None:
                ratio = self._effective_size_pixel_ratio()
                if ratio > 0.0:
                    width = physical[0] / ratio
                    height = physical[1] / ratio
                    return self._apply_canvas_size(width, height)
        size = get_canvas_logical_size(self.canvas)
        if size is None:
            return False
        width, height = size
        return self._apply_canvas_size(width, height)

    def _quantize_size(self, value: float) -> int:
        if self._resize_size_quantization == "round":
            return int(round(value))
        return int(value)

    @staticmethod
    def _coerce_size2(value: object) -> tuple[float, float] | None:
        if not (isinstance(value, (tuple, list)) and len(value) >= 2):
            return None
        a, b = value[0], value[1]
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return None
        return float(a), float(b)

    def _get_canvas_physical_size(self) -> tuple[float, float] | None:
        get_physical_size = getattr(self.canvas, "get_physical_size", None)
        if not callable(get_physical_size):
            return None
        try:
            return self._coerce_size2(get_physical_size())
        except Exception:
            return None

    def _get_canvas_pixel_ratio(self) -> float | None:
        get_pixel_ratio = getattr(self.canvas, "get_pixel_ratio", None)
        if not callable(get_pixel_ratio):
            return None
        try:
            ratio = get_pixel_ratio()
        except Exception:
            return None
        if not isinstance(ratio, (int, float)):
            return None
        ratio_f = float(ratio)
        return ratio_f if ratio_f > 0.0 else None

    def _effective_size_pixel_ratio(self) -> float:
        if self._renderer_force_pixel_ratio > 0.0:
            return self._renderer_force_pixel_ratio
        canvas_ratio = self._get_canvas_pixel_ratio()
        if canvas_ratio is not None:
            return canvas_ratio
        renderer_ratio = getattr(self.renderer, "pixel_ratio", None)
        if isinstance(renderer_ratio, (int, float)) and float(renderer_ratio) > 0.0:
            return float(renderer_ratio)
        return 1.0

    def _apply_renderer_pixel_ratio_experiment(self) -> None:
        if self._renderer_force_pixel_ratio <= 0.0:
            return
        forced = float(self._renderer_force_pixel_ratio)
        for attr in ("pixel_ratio", "device_pixel_ratio", "_pixel_ratio"):
            if hasattr(self.renderer, attr):
                try:
                    setattr(self.renderer, attr, forced)
                except Exception:
                    pass
        target = getattr(self.renderer, "target", None)
        if target is not None:
            for attr in ("pixel_ratio", "device_pixel_ratio", "_pixel_ratio"):
                if hasattr(target, attr):
                    try:
                        setattr(target, attr, forced)
                    except Exception:
                        pass

    @staticmethod
    def _to_scalar(value: object) -> object:
        if isinstance(value, (str, bool, int, float)):
            return value
        return str(value)

    def _collect_backend_probe(self) -> dict[str, object]:
        probe: dict[str, object] = {}
        for attr in ("backend", "backend_type", "present_mode", "surface_format"):
            value = getattr(self.renderer, attr, None)
            if value is not None:
                probe[f"renderer.{attr}"] = self._to_scalar(value)
        target = getattr(self.renderer, "target", None)
        if target is not None:
            for attr in ("backend", "backend_type", "present_mode", "surface_format"):
                value = getattr(target, attr, None)
                if value is not None:
                    probe[f"renderer.target.{attr}"] = self._to_scalar(value)
        device = getattr(self.renderer, "device", None)
        if device is None:
            device = getattr(self.renderer, "_device", None)
        if device is not None:
            probe["device.type"] = f"{device.__class__.__module__}.{device.__class__.__name__}"
            adapter = getattr(device, "adapter", None)
            if adapter is not None:
                info = getattr(adapter, "info", None)
                if info is not None:
                    if isinstance(info, dict):
                        probe["adapter.info"] = {
                            str(k): self._to_scalar(v)
                            for k, v in info.items()
                            if isinstance(k, str)
                        }
                    else:
                        adapter_info: dict[str, object] = {}
                        for attr in (
                            "backend_type",
                            "device",
                            "description",
                            "vendor",
                            "architecture",
                            "driver",
                            "adapter_type",
                        ):
                            value = getattr(info, attr, None)
                            if value is not None:
                                adapter_info[attr] = self._to_scalar(value)
                        if adapter_info:
                            probe["adapter.info"] = adapter_info
        return probe

    def _collect_backend_state(self) -> dict[str, object]:
        state: dict[str, object] = {
            "window_size": [int(self.width), int(self.height)],
            "viewport_revision": int(self._viewport_revision),
        }

        logical_size = get_canvas_logical_size(self.canvas)
        if logical_size is not None:
            state["canvas_logical_size"] = [logical_size[0], logical_size[1]]

        physical = self._get_canvas_physical_size()
        if physical is not None:
            state["canvas_physical_size"] = [physical[0], physical[1]]

        canvas_ratio = self._get_canvas_pixel_ratio()
        if canvas_ratio is not None:
            state["canvas_pixel_ratio"] = canvas_ratio

        if hasattr(self.camera, "width") and hasattr(self.camera, "height"):
            try:
                state["camera_size"] = [float(self.camera.width), float(self.camera.height)]
            except Exception:
                pass

        renderer_sizes: dict[str, list[float]] = {}
        for attr in ("logical_size", "physical_size", "target_size", "size"):
            value = getattr(self.renderer, attr, None)
            size2 = self._coerce_size2(value)
            if size2 is not None:
                renderer_sizes[attr] = [size2[0], size2[1]]
        target = getattr(self.renderer, "target", None)
        if target is not None:
            for attr in ("logical_size", "physical_size", "size"):
                value = getattr(target, attr, None)
                size2 = self._coerce_size2(value)
                if size2 is not None:
                    renderer_sizes[f"target.{attr}"] = [size2[0], size2[1]]
        if renderer_sizes:
            state["renderer_sizes"] = renderer_sizes
            renderer_logical = renderer_sizes.get("logical_size")
            renderer_physical = renderer_sizes.get("physical_size")
            if (
                renderer_logical is not None
                and renderer_physical is not None
                and renderer_logical[0] > 0.0
                and renderer_logical[1] > 0.0
            ):
                state["renderer_physical_ratio"] = [
                    renderer_physical[0] / renderer_logical[0],
                    renderer_physical[1] / renderer_logical[1],
                ]

        renderer_scalars: dict[str, float] = {}
        for attr in ("pixel_ratio", "device_pixel_ratio", "_pixel_ratio"):
            value = getattr(self.renderer, attr, None)
            if isinstance(value, (int, float)):
                renderer_scalars[f"renderer.{attr}"] = float(value)
        target = getattr(self.renderer, "target", None)
        if target is not None:
            for attr in ("pixel_ratio", "device_pixel_ratio", "_pixel_ratio"):
                value = getattr(target, attr, None)
                if isinstance(value, (int, float)):
                    renderer_scalars[f"renderer.target.{attr}"] = float(value)
        if renderer_scalars:
            state["renderer_scalars"] = renderer_scalars
        backend_probe = self._collect_backend_probe()
        if backend_probe:
            state["backend_probe"] = backend_probe

        return state

    @staticmethod
    def _package_version(name: str) -> str:
        try:
            return version(name)
        except PackageNotFoundError:
            return "unknown"

    def _resolve_runtime_info(self) -> dict[str, object]:
        renderer_type = f"{self.renderer.__class__.__module__}.{self.renderer.__class__.__name__}"
        return {
            "canvas_type": f"{self.canvas.__class__.__module__}.{self.canvas.__class__.__name__}",
            "renderer_type": renderer_type,
            "camera_type": f"{self.camera.__class__.__module__}.{self.camera.__class__.__name__}",
            "versions": {
                "pygfx": self._package_version("pygfx"),
                "wgpu": self._package_version("wgpu"),
                "rendercanvas": self._package_version("rendercanvas"),
            },
            "resize_experiment": {
                "force_invalidate": self._resize_force_invalidate,
                "size_source_mode": self._resize_size_source_mode,
                "size_quantization": self._resize_size_quantization,
                "camera_set_view_size": self._resize_camera_set_view_size,
                "sync_from_physical_size": self._resize_sync_from_physical_size,
            },
            "backend_experiment": {
                "renderer_force_pixel_ratio": self._renderer_force_pixel_ratio,
            },
            "render_loop": {
                "mode": self._render_loop_mode,
                "fps_cap": self._render_fps_cap,
                "vsync": self._render_vsync,
                "resize_cooldown_ms": int(self._render_resize_cooldown_s * 1000.0),
            },
        }

    def begin_frame(self) -> None:
        """Start a frame and reset active key trackers."""
        if self._frame_active:
            return
        self._frame_active = True
        self._frame_viewport = self._viewport_transform()
        self._frame_viewport_revision = self._viewport_revision
        self._frame_window_size = (float(self.width), float(self.height))
        self._active_rect_keys.clear()
        self._active_line_keys.clear()
        self._active_text_keys.clear()
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_frame_state(
                stage="begin",
                payload={
                    "rect_nodes": len(self._rect_nodes),
                    "line_nodes": len(self._line_nodes),
                    "text_nodes": len(self._text_nodes),
                    "active_rect_keys": len(self._active_rect_keys),
                    "active_line_keys": len(self._active_line_keys),
                    "active_text_keys": len(self._active_text_keys),
                    "viewport_revision": self._viewport_revision,
                },
            )

    def _viewport_transform(self) -> tuple[float, float, float, float]:
        return viewport_transform(
            width=self.width,
            height=self.height,
            design_width=self.design_width,
            design_height=self.design_height,
            preserve_aspect=self.preserve_aspect,
        )

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return to_design_space(
            x=x,
            y=y,
            width=self.width,
            height=self.height,
            design_width=self.design_width,
            design_height=self.design_height,
            preserve_aspect=self.preserve_aspect,
        )

    def end_frame(self) -> None:
        """Hide dynamic retained nodes that were not touched this frame."""
        if not self._frame_active:
            return
        hidden_rect = [
            k
            for k in self._rect_nodes
            if k not in self._static_rect_keys and k not in self._active_rect_keys
        ]
        hidden_line = [
            k
            for k in self._line_nodes
            if k not in self._static_line_keys and k not in self._active_line_keys
        ]
        hidden_text = [
            k
            for k in self._text_nodes
            if k not in self._static_text_keys and k not in self._active_text_keys
        ]
        hide_inactive_nodes(self._rect_nodes, self._static_rect_keys, self._active_rect_keys)
        hide_inactive_nodes(self._line_nodes, self._static_line_keys, self._active_line_keys)
        hide_inactive_nodes(self._text_nodes, self._static_text_keys, self._active_text_keys)
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_frame_state(
                stage="end",
                payload={
                    "rect_nodes": len(self._rect_nodes),
                    "line_nodes": len(self._line_nodes),
                    "text_nodes": len(self._text_nodes),
                    "hidden_rect_keys": hidden_rect[:50],
                    "hidden_line_keys": hidden_line[:50],
                    "hidden_text_keys": hidden_text[:50],
                    "hidden_rect_count": len(hidden_rect),
                    "hidden_line_count": len(hidden_line),
                    "hidden_text_count": len(hidden_text),
                    "viewport_revision": self._viewport_revision,
                },
            )
        self._frame_active = False
        self._frame_viewport = None
        self._frame_viewport_revision = None
        self._frame_window_size = None

    def _active_viewport_transform(self) -> tuple[float, float, float, float]:
        if self._frame_active and self._frame_viewport is not None:
            return self._frame_viewport
        return self._viewport_transform()

    def _active_viewport_revision(self) -> int:
        if self._frame_active and self._frame_viewport_revision is not None:
            return self._frame_viewport_revision
        return self._viewport_revision

    def _active_window_size(self) -> tuple[float, float]:
        if self._frame_active and self._frame_window_size is not None:
            return self._frame_window_size
        return (float(self.width), float(self.height))

    def clear_dynamic(self) -> None:
        """Compatibility wrapper for older call-sites."""
        self.begin_frame()
        self.end_frame()

    @staticmethod
    def _resolve_pass_descriptor(pass_name: str) -> _PassDescriptor:
        normalized = pass_name.strip().lower()
        if normalized in {"world", "geometry"}:
            return _PassDescriptor(canonical_name="world", priority=0)
        if normalized in {"ui", "overlay"}:
            return _PassDescriptor(canonical_name="ui", priority=100)
        if normalized.startswith("post"):
            return _PassDescriptor(canonical_name="post", priority=200)
        return _PassDescriptor(canonical_name="custom", priority=50)

    def _build_pass_batches(self, snapshot: RenderSnapshot) -> tuple[_RenderPassBatch, ...]:
        indexed_passes = list(enumerate(snapshot.passes))
        indexed_passes.sort(
            key=lambda item: (
                self._resolve_pass_descriptor(str(getattr(item[1], "name", ""))).priority,
                str(getattr(item[1], "name", "")),
                int(item[0]),
            )
        )
        batches: list[_RenderPassBatch] = []
        for _, render_pass in indexed_passes:
            commands = tuple(
                sorted(
                    render_pass.commands,
                    key=lambda command: (
                        int(getattr(command, "layer", 0)),
                        str(getattr(command, "kind", "")),
                        str(getattr(command, "sort_key", "")),
                    ),
                )
            )
            batches.append(_RenderPassBatch(name=str(render_pass.name), commands=commands))
        return tuple(batches)

    def _execute_immediate_command(self, command: RenderCommand) -> None:
        immediate_snapshot = RenderSnapshot(
            frame_index=-1,
            passes=(RenderPassSnapshot(name="immediate", commands=(command,)),),
        )
        batches = self._build_pass_batches(immediate_snapshot)
        self._execute_pass_batches(batches)

    def _emit_render_stage(
        self,
        *,
        stage: str,
        value: Any | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        hub.emit_fast(
            category="render",
            name=f"render.stage.{stage}",
            tick=max(0, self._viewport_revision),
            value=value,
            metadata=metadata or {},
        )

    @staticmethod
    def _as_float(value: object, default: float) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        return default

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        return default

    def _execute_pass_batches(self, batches: tuple[_RenderPassBatch, ...]) -> int:
        executed_commands = 0
        for pass_index, pass_batch in enumerate(batches):
            self._emit_render_stage(
                stage="execute_pass.begin",
                metadata={
                    "pass_name": pass_batch.name,
                    "pass_index": pass_index,
                    "command_count": len(pass_batch.commands),
                },
            )
            for command in pass_batch.commands:
                self._execute_render_command(command)
                executed_commands += 1
            self._emit_render_stage(
                stage="execute_pass.end",
                metadata={
                    "pass_name": pass_batch.name,
                    "pass_index": pass_index,
                    "command_count": len(pass_batch.commands),
                },
            )
        return executed_commands

    def _execute_render_command(self, command: RenderCommand) -> None:
        payload = {str(key): value for key, value in command.data}
        kind = str(command.kind)
        if kind == "fill_window":
            key = payload.get("key")
            color = payload.get("color")
            z = self._as_float(payload.get("z"), -100.0)
            if isinstance(key, str) and isinstance(color, str):
                self._apply_fill_window(key, color, z)
            return
        if kind == "rect":
            color = payload.get("color")
            if not isinstance(color, str):
                return
            rect_key = payload.get("key")
            self._apply_add_rect(
                key=rect_key if isinstance(rect_key, str) else None,
                x=self._as_float(payload.get("x"), 0.0),
                y=self._as_float(payload.get("y"), 0.0),
                w=self._as_float(payload.get("w"), 0.0),
                h=self._as_float(payload.get("h"), 0.0),
                color=color,
                z=self._as_float(payload.get("z"), 0.0),
                static=bool(payload.get("static", False)),
            )
            return
        if kind == "grid":
            key = payload.get("key")
            color = payload.get("color")
            if not isinstance(key, str) or not isinstance(color, str):
                return
            self._apply_add_grid(
                key=key,
                x=self._as_float(payload.get("x"), 0.0),
                y=self._as_float(payload.get("y"), 0.0),
                width=self._as_float(payload.get("width"), 0.0),
                height=self._as_float(payload.get("height"), 0.0),
                lines=self._as_int(payload.get("lines"), 0),
                color=color,
                z=self._as_float(payload.get("z"), 0.5),
                static=bool(payload.get("static", False)),
            )
            return
        if kind == "text":
            text = payload.get("text")
            if not isinstance(text, str):
                return
            text_key = payload.get("key")
            self._apply_add_text(
                key=text_key if isinstance(text_key, str) else None,
                text=text,
                x=self._as_float(payload.get("x"), 0.0),
                y=self._as_float(payload.get("y"), 0.0),
                font_size=self._as_float(payload.get("font_size"), 18.0),
                color=str(payload.get("color", "#ffffff")),
                anchor=str(payload.get("anchor", "top-left")),
                z=self._as_float(payload.get("z"), 2.0),
                static=bool(payload.get("static", False)),
            )
            return
        if kind == "title":
            title = payload.get("title")
            if isinstance(title, str):
                self._apply_set_title(title)

    def add_rect(
        self,
        key: str | None,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
    ) -> None:
        """Add a filled rectangle via immediate batch path."""
        command = RenderCommand(
            kind="rect",
            layer=int(round(float(z) * 100.0)),
            data=(
                ("key", key),
                ("x", float(x)),
                ("y", float(y)),
                ("w", float(w)),
                ("h", float(h)),
                ("color", str(color)),
                ("z", float(z)),
                ("static", bool(static)),
            ),
        )
        self._execute_immediate_command(command)

    def _apply_add_rect(
        self,
        key: str | None,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
    ) -> None:
        """Add a filled rectangle."""
        sx, sy, ox, oy = self._active_viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = w * sx
        th = h * sy
        viewport_revision = self._active_viewport_revision()
        before = self._rect_transformed_props.get(key) if key is not None else None
        after = (tx, ty, tw, th)
        if key is not None:
            self._rect_transformed_props[key] = after
        upsert_rect(
            gfx=gfx,
            scene=self.scene,
            key=key,
            x=x,
            y=y,
            w=w,
            h=h,
            color=color,
            z=z,
            tx=tx,
            ty=ty,
            tw=tw,
            th=th,
            viewport_revision=viewport_revision,
            rect_nodes=self._rect_nodes,
            rect_props=self._rect_props,
            rect_viewport_rev=self._rect_viewport_rev,
            static_rect_keys=self._static_rect_keys,
            active_rect_keys=self._active_rect_keys,
            dynamic_nodes=self._dynamic_nodes,
            static=static,
        )
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            if key is None:
                action = "dynamic"
            elif before is None:
                action = "create"
            elif before != after:
                action = "update"
            else:
                action = "reuse"
            diagnostics.note_retained_op(
                primitive_type="rect",
                key=key,
                action=action,
                viewport_revision=viewport_revision,
                before=before,
                after=after,
            )
            diagnostics.note_primitive(
                primitive_type="rect",
                key=key,
                source=(x, y, w, h),
                transformed=(tx, ty, tw, th),
                z=z,
                viewport_revision=viewport_revision,
            )
        if key is not None and key.startswith("button:bg:"):
            if diagnostics is not None:
                diagnostics.note_button_rect(
                    key.removeprefix("button:bg:"),
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    tx=tx,
                    ty=ty,
                    tw=tw,
                    th=th,
                )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    (
                        "ui_button_geometry id=%s source=(%.2f,%.2f,%.2f,%.2f) "
                        "transformed=(%.2f,%.2f,%.2f,%.2f)"
                    ),
                    key.removeprefix("button:bg:"),
                    x,
                    y,
                    w,
                    h,
                    tx,
                    ty,
                    tw,
                    th,
                )

    def add_grid(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        lines: int,
        color: str,
        z: float = 0.5,
        static: bool = False,
    ) -> None:
        """Add a batched line-segment grid via immediate batch path."""
        command = RenderCommand(
            kind="grid",
            layer=int(round(float(z) * 100.0)),
            data=(
                ("key", str(key)),
                ("x", float(x)),
                ("y", float(y)),
                ("width", float(width)),
                ("height", float(height)),
                ("lines", int(lines)),
                ("color", str(color)),
                ("z", float(z)),
                ("static", bool(static)),
            ),
        )
        self._execute_immediate_command(command)

    def _apply_add_grid(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        lines: int,
        color: str,
        z: float = 0.5,
        static: bool = False,
    ) -> None:
        """Add a batched line-segment grid."""
        sx, sy, ox, oy = self._active_viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = width * sx
        th = height * sy
        viewport_revision = self._active_viewport_revision()
        before = self._line_transformed_props.get(key)
        after = (tx, ty, tw, th)
        self._line_transformed_props[key] = after
        upsert_grid(
            gfx=gfx,
            scene=self.scene,
            key=key,
            x=x,
            y=y,
            width=width,
            height=height,
            lines=lines,
            color=color,
            z=z,
            tx=tx,
            ty=ty,
            tw=tw,
            th=th,
            viewport_revision=viewport_revision,
            line_nodes=self._line_nodes,
            line_props=self._line_props,
            line_viewport_rev=self._line_viewport_rev,
            static_line_keys=self._static_line_keys,
            active_line_keys=self._active_line_keys,
            static=static,
        )
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            if before is None:
                action = "create"
            elif before != after:
                action = "update"
            else:
                action = "reuse"
            diagnostics.note_retained_op(
                primitive_type="grid",
                key=key,
                action=action,
                viewport_revision=viewport_revision,
                before=before,
                after=after,
            )
            diagnostics.note_primitive(
                primitive_type="grid",
                key=key,
                source=(x, y, width, height),
                transformed=(tx, ty, tw, th),
                z=z,
                viewport_revision=viewport_revision,
            )

    def add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = "#ffffff",
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        """Add screen-space text via immediate batch path."""
        command = RenderCommand(
            kind="text",
            layer=int(round(float(z) * 100.0)),
            data=(
                ("key", key),
                ("text", str(text)),
                ("x", float(x)),
                ("y", float(y)),
                ("font_size", float(font_size)),
                ("color", str(color)),
                ("anchor", str(anchor)),
                ("z", float(z)),
                ("static", bool(static)),
            ),
        )
        self._execute_immediate_command(command)

    def _apply_add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = "#ffffff",
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        """Add screen-space text."""
        sx, sy, ox, oy = self._active_viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tsize = font_size * min(sx, sy)
        viewport_revision = self._active_viewport_revision()
        before = self._text_transformed_props.get(key) if key is not None else None
        after = (tx, ty, tsize, tsize)
        if key is not None:
            self._text_transformed_props[key] = after
        upsert_text(
            gfx=gfx,
            scene=self.scene,
            key=key,
            text=text,
            x=x,
            y=y,
            font_size=font_size,
            color=color,
            anchor=anchor,
            z=z,
            tx=tx,
            ty=ty,
            tsize=tsize,
            viewport_revision=viewport_revision,
            text_nodes=self._text_nodes,
            text_props=self._text_props,
            text_viewport_rev=self._text_viewport_rev,
            static_text_keys=self._static_text_keys,
            active_text_keys=self._active_text_keys,
            dynamic_nodes=self._dynamic_nodes,
            static=static,
        )
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            if key is None:
                action = "dynamic"
            elif before is None:
                action = "create"
            elif before != after:
                action = "update"
            else:
                action = "reuse"
            diagnostics.note_retained_op(
                primitive_type="text",
                key=key,
                action=action,
                viewport_revision=viewport_revision,
                before=before,
                after=after,
            )
            diagnostics.note_primitive(
                primitive_type="text",
                key=key,
                source=(x, y, font_size, font_size),
                transformed=(tx, ty, tsize, tsize),
                z=z,
                viewport_revision=viewport_revision,
            )
        if key is not None and key.startswith("button:text:"):
            if diagnostics is not None:
                diagnostics.note_button_text(key.removeprefix("button:text:"), text_size=tsize)

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        """Fill the entire window via immediate batch path."""
        command = RenderCommand(
            kind="fill_window",
            layer=int(round(float(z) * 100.0)),
            data=(("key", str(key)), ("color", str(color)), ("z", float(z))),
        )
        self._execute_immediate_command(command)

    def _apply_fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        """Fill the entire window in window-space coordinates."""
        color_value = cast(Any, color)
        tw, th = self._active_window_size()
        tx = 0.0
        ty = 0.0
        viewport_revision = self._active_viewport_revision()
        before = self._rect_transformed_props.get(key)
        after = (tx, ty, tw, th)
        self._rect_transformed_props[key] = after
        if key in self._rect_nodes:
            node = self._rect_nodes[key]
            new_props = (tx, ty, tw, th, color, z)
            needs_update = (
                self._rect_props.get(key) != new_props
                or self._rect_viewport_rev.get(key, -1) != viewport_revision
            )
            if needs_update:
                node.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
                node.geometry = gfx.plane_geometry(tw, th)
                if hasattr(node, "material"):
                    node.material.color = color_value
                self._rect_props[key] = new_props
                self._rect_viewport_rev[key] = viewport_revision
            node.visible = True
            self._active_rect_keys.add(key)
            diagnostics = self._ui_diagnostics
            if diagnostics is not None:
                action = "update" if before is not None and before != after else "reuse"
                diagnostics.note_retained_op(
                    primitive_type="window_rect",
                    key=key,
                    action=action,
                    viewport_revision=viewport_revision,
                    before=before,
                    after=after,
                )
                diagnostics.note_primitive(
                    primitive_type="window_rect",
                    key=key,
                    source=(tx, ty, tw, th),
                    transformed=(tx, ty, tw, th),
                    z=z,
                    viewport_revision=viewport_revision,
                )
            return

        mesh = gfx.Mesh(gfx.plane_geometry(tw, th), gfx.MeshBasicMaterial(color=color))
        mesh.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
        self.scene.add(mesh)
        self._rect_nodes[key] = mesh
        self._rect_props[key] = (tx, ty, tw, th, color, z)
        self._rect_viewport_rev[key] = viewport_revision
        self._active_rect_keys.add(key)
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_retained_op(
                primitive_type="window_rect",
                key=key,
                action="create",
                viewport_revision=viewport_revision,
                before=before,
                after=after,
            )
            diagnostics.note_primitive(
                primitive_type="window_rect",
                key=key,
                source=(tx, ty, tw, th),
                transformed=(tx, ty, tw, th),
                z=z,
                viewport_revision=viewport_revision,
            )

    def set_title(self, title: str) -> None:
        """Set window title when supported by backend via immediate batch path."""
        command = RenderCommand(kind="title", layer=0, data=(("title", str(title)),))
        self._execute_immediate_command(command)

    def _apply_set_title(self, title: str) -> None:
        """Set window title when supported by backend."""
        self.title = title
        canvas = self._require_canvas()
        if hasattr(canvas, "set_title"):
            canvas.set_title(title)

    def invalidate(self) -> None:
        """Schedule one redraw."""
        if self._is_closed:
            return
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_frame_reason("invalidate")
        canvas = self._require_canvas()
        if hasattr(canvas, "request_draw"):
            canvas.request_draw()

    def set_diagnostics_hub(self, hub: DiagnosticHub | None) -> None:
        """Attach optional engine diagnostics hub for render/resize events."""
        self._diagnostics_hub = hub
        if hub is not None:
            self._emit_render_projection_events(reason="hub_attached")

    def note_frame_reason(self, reason: str) -> None:
        """Record a frame trigger reason for diagnostics."""
        diagnostics = self._ui_diagnostics
        if diagnostics is not None:
            diagnostics.note_frame_reason(reason)

    def ui_diagnostics_summary(self) -> dict[str, int] | None:
        """Return compact UI diagnostics summary for overlay consumption."""
        diagnostics = self._ui_diagnostics
        if diagnostics is None:
            return None
        return diagnostics.latest_summary()

    def ui_trace_scope(
        self, name: str
    ) -> Callable[[Callable[..., object]], Callable[..., object]] | None:
        """Return a decorator for scoped UI diagnostics tracing when enabled."""
        diagnostics = self._ui_diagnostics
        if diagnostics is None:
            return None
        return diagnostics.scope_decorator(name)

    def _continuous_mode_active(self, now: float) -> bool:
        if self._render_loop_mode == "continuous":
            return True
        if self._render_loop_mode == "continuous_during_resize":
            return now <= self._resize_continuous_until
        return False

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        """Render one immutable snapshot payload."""
        started_here = not self._frame_active
        if started_here:
            self.begin_frame()
            self._emit_render_stage(
                stage="begin_frame",
                metadata={
                    "viewport_revision": int(self._viewport_revision),
                    "size": (int(self.width), int(self.height)),
                },
            )
        try:
            batches = self._build_pass_batches(snapshot)
            self._emit_render_stage(
                stage="build_batches",
                value={"pass_count": len(batches)},
                metadata={
                    "frame_index": int(getattr(snapshot, "frame_index", -1)),
                    "pass_names": [batch.name for batch in batches],
                },
            )
            executed_count = self._execute_pass_batches(batches)
            self._emit_render_stage(
                stage="execute_passes",
                value={"command_count": executed_count},
                metadata={"pass_count": len(batches)},
            )
        finally:
            if started_here:
                self.present()
                self.end_frame()
                self._emit_render_stage(
                    stage="end_frame",
                    metadata={
                        "viewport_revision": int(self._viewport_revision),
                        "size": (int(self.width), int(self.height)),
                    },
                )

    def present(self, *, frame_start: float | None = None) -> None:
        """Present the current prepared scene to the backend surface."""
        present_start = perf_counter()
        self.renderer.render(self.scene, self.camera)
        present_end = perf_counter()
        frame_ms = (
            (present_end - frame_start) * 1000.0
            if isinstance(frame_start, (int, float))
            else (present_end - present_start) * 1000.0
        )
        hub = self._diagnostics_hub
        if hub is not None:
            draw_count = 0
            try:
                draw_count = int(len(getattr(self.scene, "children", ())))
            except Exception:
                draw_count = 0
            hub.emit_fast(
                category="render",
                name="render.frame_ms",
                tick=max(0, self._viewport_revision),
                value=frame_ms,
                metadata={
                    "viewport_revision": self._viewport_revision,
                    "size": (int(self.width), int(self.height)),
                },
            )
            hub.emit_fast(
                category="render",
                name="render.present",
                tick=max(0, self._viewport_revision),
                value=frame_ms,
                metadata={
                    "draw_count": draw_count,
                    "size": (int(self.width), int(self.height)),
                },
            )
            hub.emit_fast(
                category="render",
                name="render.present_interval",
                tick=max(0, self._viewport_revision),
                value=frame_ms,
                metadata={
                    "vsync": bool(self._render_vsync),
                    "fps_cap": float(self._render_fps_cap),
                    "mode": self._render_loop_mode,
                },
            )
            self._emit_render_stage(
                stage="present",
                value={"frame_ms": frame_ms},
                metadata={"draw_count": draw_count},
            )
            apply_ts = self._last_resize_applied_ts
            if apply_ts is not None:
                apply_to_frame_ms = (present_end - apply_ts) * 1000.0
                hub.emit_fast(
                    category="render",
                    name="render.resize_event",
                    tick=max(0, self._viewport_revision),
                    value={"width": int(self.width), "height": int(self.height)},
                    metadata={
                        "event_to_apply_ms": self._last_resize_event_to_apply_ms,
                        "apply_to_frame_ms": apply_to_frame_ms,
                        "viewport": self._viewport_transform(),
                    },
                )
                self._last_resize_applied_ts = None
                self._last_resize_event_to_apply_ms = None

    def _continuous_frame_due(self, now: float) -> bool:
        if self._render_loop_mode == "continuous":
            return True
        if self._render_fps_cap <= 0.0:
            return True
        if self._next_continuous_frame_due <= 0.0:
            return True
        return now >= self._next_continuous_frame_due

    def _mark_continuous_frame_scheduled(self, now: float) -> None:
        if self._render_fps_cap <= 0.0:
            self._next_continuous_frame_due = 0.0
            return
        self._next_continuous_frame_due = now + (1.0 / self._render_fps_cap)

    def _schedule_next_continuous_frame(self) -> None:
        if self._is_closed:
            return
        canvas = self._require_canvas()
        if hasattr(canvas, "request_draw"):
            canvas.request_draw()

    def _require_canvas(self) -> Any:
        canvas = self.canvas
        if canvas is None:
            raise RuntimeError("renderer canvas unavailable")
        return canvas

    def run(self, draw_callback: Callable[[], None]) -> None:
        """Start draw loop."""
        self._draw_callback = draw_callback

        def _draw_frame() -> None:
            if self._draw_failed or self._is_closed:
                return
            frame_start = perf_counter()
            continuous_active = self._continuous_mode_active(frame_start)
            if continuous_active and not self._continuous_frame_due(frame_start):
                self._schedule_next_continuous_frame()
                return
            try:
                self._apply_renderer_pixel_ratio_experiment()
                if self._resize_size_source_mode != "event_only":
                    self._sync_size_from_canvas()
                diagnostics = self._ui_diagnostics
                if diagnostics is not None:
                    diagnostics.begin_frame(frame_render_ts=frame_start)
                    sx, sy, ox, oy = self._viewport_transform()
                    diagnostics.note_viewport(
                        width=self.width,
                        height=self.height,
                        viewport_revision=self._viewport_revision,
                        sx=sx,
                        sy=sy,
                        ox=ox,
                        oy=oy,
                    )
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "ui_projection revision=%d viewport=(sx=%.4f,sy=%.4f,ox=%.2f,oy=%.2f)",
                            self._viewport_revision,
                            sx,
                            sy,
                            ox,
                            oy,
                        )
                    diagnostics.note_frame_state(
                        stage="draw_pre",
                        payload={
                            **self._collect_backend_state(),
                            "render_loop_mode": self._render_loop_mode,
                            "continuous_active": continuous_active,
                            "render_fps_cap": self._render_fps_cap,
                            "resize_continuous_until": self._resize_continuous_until,
                        },
                    )
                if self._draw_callback is None:
                    return
                self.begin_frame()
                self._emit_render_stage(
                    stage="begin_frame",
                    metadata={
                        "viewport_revision": int(self._viewport_revision),
                        "size": (int(self.width), int(self.height)),
                    },
                )
                self._draw_callback()
                if self._is_closed:
                    return
                self.present(frame_start=frame_start)
                self.end_frame()
                self._emit_render_stage(
                    stage="end_frame",
                    metadata={
                        "viewport_revision": int(self._viewport_revision),
                        "size": (int(self.width), int(self.height)),
                    },
                )
                if diagnostics is not None:
                    diagnostics.note_frame_state(
                        stage="draw_post",
                        payload={
                            **self._collect_backend_state(),
                            "render_loop_mode": self._render_loop_mode,
                            "continuous_active": continuous_active,
                            "render_fps_cap": self._render_fps_cap,
                        },
                    )
                    diagnostics.end_frame()
                if self._render_loop_mode == "continuous_during_resize" and continuous_active:
                    now = perf_counter()
                    self._mark_continuous_frame_scheduled(now)
                    self._schedule_next_continuous_frame()
            except Exception:  # pylint: disable=broad-exception-caught
                self.end_frame()
                hub = self._diagnostics_hub
                if hub is not None:
                    hub.emit_fast(
                        category="error",
                        name="render.unhandled_exception",
                        tick=max(0, self._viewport_revision),
                        level="error",
                        metadata={"message": "unhandled_exception_in_draw_loop"},
                    )
                self._draw_failed = True
                logger.exception("unhandled_exception_in_draw_loop")
                self.close()

        canvas = self._require_canvas()
        canvas.request_draw(_draw_frame)
        self.invalidate()
        if self._owns_canvas and rc_auto is not None:
            run_backend_loop(rc_auto)

    def close(self) -> None:
        """Close canvas and stop backend loop when possible."""
        if self._is_closed:
            return
        self._is_closed = True
        canvas = self._require_canvas()
        if self._owns_canvas and hasattr(canvas, "close"):
            canvas.close()
        if self._owns_canvas and rc_auto is not None:
            stop_backend_loop(rc_auto)

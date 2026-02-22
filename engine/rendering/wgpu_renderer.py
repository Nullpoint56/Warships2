"""WGPU-backed renderer implementation scaffold."""

from __future__ import annotations

from importlib import import_module
import os
import re
import sys
import threading
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Protocol, cast

from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.api.window import SurfaceHandle, WindowResizeEvent
from engine.rendering.scene_runtime import resolve_preserve_aspect
from engine.rendering.scene_viewport import to_design_space as viewport_to_design_space
from engine.rendering.scene_viewport import viewport_transform
from engine.runtime.config import RuntimeConfig, get_runtime_config, set_runtime_config

if TYPE_CHECKING:
    from engine.diagnostics.hub import DiagnosticHub

def _optional_import(name: str) -> Any | None:
    try:
        return import_module(name)
    except Exception:
        return None


_NP = _optional_import("numpy")
_HB = _optional_import("uharfbuzz")
_COMMAND_PAYLOAD_CACHE_MAX = 20_000
_COLOR_CACHE_MAX = 512
_TRANSFORM_CACHE_MAX = 20_000
_DEFAULT_UI_DESIGN_WIDTH = 1200
_DEFAULT_UI_DESIGN_HEIGHT = 720
_COMMAND_COLOR_CACHE: dict[object, tuple[float, float, float, float]] = {}
_COMMAND_LINEAR_COLOR_CACHE: dict[
    tuple[float, float, float, float], tuple[float, float, float, float]
] = {}
_TRANSFORM_VALUES_CACHE: dict[int, tuple[object, tuple[float, ...]]] = {}


class _Backend(Protocol):
    """Private backend contract for the renderer internals."""

    def begin_frame(self) -> None:
        """Prepare one backend frame."""

    def draw_packets(
        self,
        pass_name: str,
        packets: tuple["_DrawPacket", ...],
        *,
        pass_signature: tuple[object, ...] | None = None,
    ) -> None:
        """Encode and submit packets for one pass."""

    def present(self) -> None:
        """Present rendered frame."""

    def end_frame(self) -> None:
        """Finalize backend frame state."""

    def close(self) -> None:
        """Release backend resources."""

    def set_title(self, title: str) -> None:
        """Set title if backend supports it."""

    def reconfigure(self, event: WindowResizeEvent) -> None:
        """Apply resize/surface reconfigure."""

    def resize_telemetry(self) -> dict[str, object]:
        """Return latest resize/reconfigure telemetry."""


class WgpuInitError(RuntimeError):
    """Renderer backend initialization failure with structured details."""

    def __init__(self, message: str, *, details: dict[str, object]) -> None:
        super().__init__(message)
        self.details = details


@dataclass(frozen=True, slots=True)
class _PassDescriptor:
    canonical_name: str
    priority: int


@dataclass(frozen=True, slots=True)
class _RenderPassBatch:
    name: str
    commands: tuple[RenderCommand, ...]


@dataclass(frozen=True, slots=True)
class _DrawPacket:
    kind: str
    layer: int
    sort_key: str
    transform: tuple[float, ...]
    data: tuple[tuple[str, object], ...]
    engine_static: bool | None = None
    engine_version: object | None = None
    engine_cache_base: tuple[object, ...] | None = None


@dataclass(frozen=True, slots=True)
class _DrawRect:
    layer: int
    x: float
    y: float
    w: float
    h: float
    color: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class _GlyphAtlasEntry:
    u0: float
    v0: float
    u1: float
    v1: float
    width: float
    height: float
    bearing_x: float
    bearing_y: float
    advance: float


@dataclass(frozen=True, slots=True)
class _GlyphPlacement:
    x: float
    y: float
    width: float
    height: float
    u0: float
    v0: float
    u1: float
    v1: float


@dataclass(frozen=True, slots=True)
class _GlyphRunLayout:
    width: float
    height: float
    baseline: float
    placements: tuple[_GlyphPlacement, ...]


@dataclass(frozen=True, slots=True)
class _ShapedGlyph:
    glyph_index: int
    x_offset: float
    y_offset: float
    x_advance: float
    y_advance: float


@dataclass(frozen=True, slots=True)
class _FontVerticalMetrics:
    ascent: float
    descent: float
    line_height: float


@dataclass(frozen=True, slots=True)
class _DrawTextQuad:
    layer: int
    x: float
    y: float
    w: float
    h: float
    u0: float
    v0: float
    u1: float
    v1: float
    color: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class _StaticPassExpandCacheEntry:
    static_draw_rects: tuple[_DrawRect, ...]
    static_text_quads: tuple[_DrawTextQuad, ...]
    static_draw_packet_keys: tuple[tuple[object, ...], ...]
    static_text_packet_keys: tuple[tuple[object, ...], ...]
    static_packet_identity: tuple[tuple[object, ...], ...]
    kind_rect_counts: tuple[tuple[str, int], ...]
    kind_text_quad_counts: tuple[tuple[str, int], ...]
    rect_count: int
    text_quad_count: int
    packet_translate_count: int


@dataclass(slots=True)
class WgpuRenderer:
    """Renderer scaffold using immutable snapshots and explicit stages."""

    surface: SurfaceHandle | None = None
    width: int = 1200
    height: int = 720
    runtime_config: RuntimeConfig | None = None
    _backend_factory: Callable[[SurfaceHandle | None], _Backend] | None = None
    _backend: _Backend = field(init=False)
    _draw_callback: Callable[[], None] | None = field(init=False, default=None)
    _closed: bool = field(init=False, default=False)
    _frame_active: bool = field(init=False, default=False)
    _immediate_commands: list[RenderCommand] = field(init=False, default_factory=list)
    _retained_commands: dict[str, RenderCommand] = field(init=False, default_factory=dict)
    _diagnostics_hub: DiagnosticHub | None = field(init=False, default=None)
    _frame_index: int = field(init=False, default=0)
    _frame_dirty: bool = field(init=False, default=False)
    _frame_presented: bool = field(init=False, default=False)
    _owner_thread_id: int = field(init=False, default=0)
    _viewport_revision: int = field(init=False, default=0)
    _logical_width: float = field(init=False, default=1200.0)
    _logical_height: float = field(init=False, default=720.0)
    _dpi_scale: float = field(init=False, default=1.0)
    _projection: tuple[float, ...] = field(init=False, default=())
    _design_width: int = field(init=False, default=1200)
    _design_height: int = field(init=False, default=720)
    _preserve_aspect: bool = field(init=False, default=False)
    _canvas: object | None = field(init=False, default=None)
    _diag_stage_events_enabled: bool = field(init=False, default=True)
    _diag_stage_sampling_n: int = field(init=False, default=1)
    _diag_profile_sampling_n: int = field(init=False, default=1)
    _auto_static_min_stable_frames: int = field(init=False, default=3)
    _auto_static_state: dict[str, tuple[object, int, int]] = field(
        init=False, default_factory=dict
    )
    _pass_static_packet_cache: dict[
        str, tuple[tuple[object, ...], tuple[tuple[int, _DrawPacket], ...]]
    ] = field(
        init=False, default_factory=dict
    )
    _command_packet_cache: dict[int, tuple[RenderCommand, _DrawPacket, str, object]] = field(
        init=False, default_factory=dict
    )
    _command_version_token_cache: dict[int, tuple[RenderCommand, object]] = field(
        init=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        self._owner_thread_id = int(threading.get_ident())
        runtime_config = self.runtime_config or get_runtime_config()
        if self.runtime_config is not None:
            set_runtime_config(runtime_config)
        design_w, design_h = _resolve_ui_design_dimensions(
            default_width=int(_DEFAULT_UI_DESIGN_WIDTH),
            default_height=int(_DEFAULT_UI_DESIGN_HEIGHT),
            runtime_config=runtime_config,
        )
        self._design_width = int(design_w)
        self._design_height = int(design_h)
        self._preserve_aspect = resolve_preserve_aspect(runtime_config)
        self._diag_stage_events_enabled = _env_flag(
            "ENGINE_DIAGNOSTICS_RENDER_STAGE_EVENTS_ENABLED", True
        )
        self._diag_stage_sampling_n = _env_int(
            "ENGINE_DIAGNOSTICS_RENDER_STAGE_SAMPLING_N",
            runtime_config.profile.diagnostics_default_sampling_n,
            minimum=1,
        )
        self._diag_profile_sampling_n = _env_int(
            "ENGINE_DIAGNOSTICS_RENDER_PROFILE_SAMPLING_N",
            runtime_config.profile.diagnostics_default_sampling_n,
            minimum=1,
        )
        self._auto_static_min_stable_frames = _env_int(
            "ENGINE_RENDER_AUTO_STATIC_MIN_STABLE_FRAMES", 3, minimum=1
        )
        self._canvas = self.surface.provider if self.surface is not None else None
        if self._backend_factory is not None:
            factory = self._backend_factory
        else:
            factory = lambda surface: _create_wgpu_backend(surface, runtime_config=runtime_config)
        self._backend = factory(self.surface)
        self._projection = _ortho_projection(width=float(self.width), height=float(self.height))

    def begin_frame(self) -> None:
        self._assert_owner_thread()
        if self._closed or self._frame_active:
            return
        self._frame_active = True
        self._frame_presented = False
        self._backend.begin_frame()
        self._emit_render_stage("begin_frame")

    def end_frame(self) -> None:
        self._assert_owner_thread()
        if self._closed or not self._frame_active:
            return
        frame_started = time.perf_counter()
        mem_before = self._traced_memory_mb()
        if self._frame_dirty and not self._frame_presented:
            build_started = time.perf_counter()
            composed = self._compose_frame_snapshot(RenderSnapshot(frame_index=self._frame_index, passes=()))
            batches = self._build_pass_batches(composed)
            build_ms = (time.perf_counter() - build_started) * 1000.0
            self._emit_render_stage(
                "build_batches",
                value={"pass_count": int(len(batches))},
            )
            execute_started = time.perf_counter()
            execute_summary = self._execute_pass_batches(batches)
            execute_ms = (time.perf_counter() - execute_started) * 1000.0
            self._emit_render_stage("execute_passes")
            present_started = time.perf_counter()
            self._backend.present()
            present_ms = (time.perf_counter() - present_started) * 1000.0
            self._emit_render_stage("present")
            self._frame_presented = True
            self._frame_dirty = False
            total_ms = (time.perf_counter() - frame_started) * 1000.0
            self._emit_render_frame_ms(total_ms)
            self._emit_render_profile_frame(
                batch_count=len(batches),
                build_ms=build_ms,
                execute_ms=execute_ms,
                present_ms=present_ms,
                total_ms=total_ms,
                mem_before_mb=mem_before,
                mem_after_mb=self._traced_memory_mb(),
                execute_summary=execute_summary,
            )
        self._frame_active = False
        self._backend.end_frame()
        self._frame_index += 1
        self._emit_render_stage("end_frame")

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
        self._submit_command(command)

    def add_style_rect(
        self,
        *,
        style_kind: str,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
        radius: float = 0.0,
        thickness: float = 1.0,
        color_secondary: str = "",
        shadow_layers: float = 0.0,
    ) -> None:
        command = RenderCommand(
            kind=str(style_kind),
            layer=int(round(float(z) * 100.0)),
            data=(
                ("key", str(key)),
                ("x", float(x)),
                ("y", float(y)),
                ("w", float(w)),
                ("h", float(h)),
                ("color", str(color)),
                ("z", float(z)),
                ("static", bool(static)),
                ("radius", float(radius)),
                ("thickness", float(thickness)),
                ("color_secondary", str(color_secondary)),
                ("shadow_layers", float(shadow_layers)),
            ),
        )
        self._submit_command(command)

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
        self._submit_command(command)

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
        self._submit_command(command)

    def set_title(self, title: str) -> None:
        self._assert_owner_thread()
        self._backend.set_title(title)

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        command = RenderCommand(
            kind="fill_window",
            layer=int(round(float(z) * 100.0)),
            data=(("key", str(key)), ("color", str(color)), ("z", float(z))),
        )
        self._submit_command(command)

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        window_w = int(max(1.0, round(float(self._logical_width))))
        window_h = int(max(1.0, round(float(self._logical_height))))
        dx, dy = viewport_to_design_space(
            x=float(x),
            y=float(y),
            width=window_w,
            height=window_h,
            design_width=self._design_width,
            design_height=self._design_height,
            preserve_aspect=bool(self._preserve_aspect),
        )
        return (float(dx), float(dy))

    def design_space_size(self) -> tuple[float, float]:
        """Return active engine design-space dimensions."""
        return (float(self._design_width), float(self._design_height))

    def invalidate(self) -> None:
        self._assert_owner_thread()
        if self._closed:
            return
        request_draw = getattr(self._canvas, "request_draw", None)
        if callable(request_draw):
            draw_callback = self._draw_callback
            if draw_callback is not None:
                try:
                    request_draw(draw_callback)
                except TypeError:
                    pass
            try:
                request_draw()
                return
            except TypeError:
                pass
            except Exception:
                pass
        if self._draw_callback is not None:
            self._draw_callback()

    def run(self, draw_callback: Callable[[], None]) -> None:
        self._assert_owner_thread()
        self._draw_callback = draw_callback
        if self._closed:
            return
        draw_callback()

    def close(self) -> None:
        self._assert_owner_thread()
        if self._closed:
            return
        self._closed = True
        self._pass_static_packet_cache.clear()
        self._command_packet_cache.clear()
        self._command_version_token_cache.clear()
        self._backend.close()

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        self._assert_owner_thread()
        started_here = not self._frame_active
        if started_here:
            self.begin_frame()
        frame_started = time.perf_counter()
        mem_before = self._traced_memory_mb()
        try:
            build_started = time.perf_counter()
            composed = self._compose_frame_snapshot(snapshot)
            batches = self._build_pass_batches(composed)
            build_ms = (time.perf_counter() - build_started) * 1000.0
            self._emit_render_stage(
                "build_batches",
                value={"pass_count": int(len(batches))},
            )
            execute_started = time.perf_counter()
            execute_summary = self._execute_pass_batches(batches)
            execute_ms = (time.perf_counter() - execute_started) * 1000.0
            self._emit_render_stage("execute_passes")
            present_started = time.perf_counter()
            self._backend.present()
            present_ms = (time.perf_counter() - present_started) * 1000.0
            self._emit_render_stage("present")
            self._frame_presented = True
            self._frame_dirty = False
            total_ms = (time.perf_counter() - frame_started) * 1000.0
            self._emit_render_frame_ms(total_ms)
            self._emit_render_profile_frame(
                batch_count=len(batches),
                build_ms=build_ms,
                execute_ms=execute_ms,
                present_ms=present_ms,
                total_ms=total_ms,
                mem_before_mb=mem_before,
                mem_after_mb=self._traced_memory_mb(),
                execute_summary=execute_summary,
            )
        finally:
            if started_here:
                self.end_frame()

    def apply_window_resize(self, event: WindowResizeEvent) -> None:
        self._assert_owner_thread()
        self._logical_width = float(event.logical_width)
        self._logical_height = float(event.logical_height)
        self._dpi_scale = max(0.01, float(event.dpi_scale))
        self.width = max(1, int(event.physical_width))
        self.height = max(1, int(event.physical_height))
        self._viewport_revision += 1
        self._projection = _ortho_projection(width=float(self.width), height=float(self.height))
        self._backend.reconfigure(event)
        telemetry = self._backend.resize_telemetry()
        self._emit_resize_diagnostics(event, telemetry)

    def set_diagnostics_hub(self, hub: DiagnosticHub | None) -> None:
        self._diagnostics_hub = hub

    def _submit_command(self, command: RenderCommand) -> None:
        key = _command_key(command)
        if key:
            self._retained_commands[key] = command
        else:
            self._immediate_commands.append(command)
        self._frame_dirty = True
        if self._frame_active:
            return
        self.render_snapshot(RenderSnapshot(frame_index=self._frame_index, passes=()))

    def _compose_frame_snapshot(self, snapshot: RenderSnapshot) -> RenderSnapshot:
        overlay_commands = list(self._retained_commands.values()) + list(self._immediate_commands)
        self._immediate_commands.clear()
        if not overlay_commands:
            return snapshot
        passes = list(snapshot.passes)
        merged = False
        for index, render_pass in enumerate(passes):
            descriptor = _resolve_pass_descriptor(render_pass.name)
            if descriptor.canonical_name == "overlay":
                passes[index] = RenderPassSnapshot(
                    name=render_pass.name,
                    commands=tuple(render_pass.commands) + tuple(overlay_commands),
                )
                merged = True
                break
        if not merged:
            passes.append(
                RenderPassSnapshot(name="overlay", commands=tuple(overlay_commands))
            )
        return RenderSnapshot(frame_index=int(snapshot.frame_index), passes=tuple(passes))

    def _build_pass_batches(self, snapshot: RenderSnapshot) -> tuple[_RenderPassBatch, ...]:
        batches: list[_RenderPassBatch] = []
        for render_pass in snapshot.passes:
            descriptor = _resolve_pass_descriptor(render_pass.name)
            keyed: list[tuple[tuple[object, ...], RenderCommand]] = []
            already_sorted = True
            previous_key: tuple[object, ...] | None = None
            for ordinal, command in enumerate(render_pass.commands):
                key = _command_sort_key(command, ordinal)
                if previous_key is not None and key < previous_key:
                    already_sorted = False
                previous_key = key
                keyed.append((key, command))
            if already_sorted:
                commands = tuple(command for _, command in keyed)
            else:
                commands = tuple(command for _, command in sorted(keyed, key=lambda item: item[0]))
            batches.append(_RenderPassBatch(name=descriptor.canonical_name, commands=commands))
        return tuple(sorted(batches, key=lambda batch: _resolve_pass_descriptor(batch.name).priority))

    def _execute_pass_batches(self, batches: tuple[_RenderPassBatch, ...]) -> dict[str, object]:
        execute_pass_packet_counts: dict[str, int] = {}
        execute_kind_packet_counts: dict[str, int] = {}
        execute_packet_count = 0
        execute_static_packet_count = 0
        execute_dynamic_packet_count = 0
        execute_packet_build_ms = 0.0
        execute_auto_static_ms = 0.0
        execute_static_packet_cache_hits = 0
        execute_backend_draw_ms = 0.0
        for batch in batches:
            batch_signature = self._command_batch_signature_cached(batch.commands)
            cached = self._pass_static_packet_cache.get(batch.name)
            static_cached_packets: dict[int, _DrawPacket] = {}
            if cached is not None:
                if cached[0] == batch_signature:
                    static_cached_packets = {int(i): p for i, p in cached[1]}
                else:
                    self._pass_static_packet_cache.pop(batch.name, None)
            packet_build_started = time.perf_counter()
            packet_list: list[_DrawPacket] = []
            static_entries_next: list[tuple[int, _DrawPacket]] = []
            for index, command in enumerate(batch.commands):
                cached_packet = static_cached_packets.get(index)
                if cached_packet is not None:
                    packet_list.append(cached_packet)
                    execute_static_packet_cache_hits += 1
                    static_entries_next.append((index, cached_packet))
                    continue
                packet, override, version_token = self._command_to_packet_cached(command)
                annotated, auto_static_ms = self._annotate_packet_static_mode(
                    packet,
                    override=override,
                    version_token=version_token,
                )
                execute_auto_static_ms += max(0.0, float(auto_static_ms))
                packet_list.append(annotated)
                if bool(getattr(annotated, "engine_static", False)):
                    static_entries_next.append((index, annotated))
            packets = tuple(packet_list)
            execute_packet_build_ms += (time.perf_counter() - packet_build_started) * 1000.0
            if static_entries_next:
                self._pass_static_packet_cache[batch.name] = (
                    batch_signature,
                    tuple(static_entries_next),
                )
            else:
                self._pass_static_packet_cache.pop(batch.name, None)
            packet_count = int(len(packets))
            execute_packet_count += packet_count
            execute_pass_packet_counts[batch.name] = (
                int(execute_pass_packet_counts.get(batch.name, 0)) + packet_count
            )
            for packet in packets:
                kind = str(getattr(packet, "kind", "")) or "unknown"
                execute_kind_packet_counts[kind] = int(execute_kind_packet_counts.get(kind, 0)) + 1
                if _packet_is_static(packet):
                    execute_static_packet_count += 1
                else:
                    execute_dynamic_packet_count += 1
            self._emit_render_stage(
                "execute_pass.begin",
                metadata={"pass_name": batch.name, "packet_count": packet_count},
            )
            backend_draw_started = time.perf_counter()
            try:
                self._backend.draw_packets(
                    batch.name,
                    packets,
                    pass_signature=batch_signature,
                )
            except TypeError:
                # Compatibility path for test doubles / legacy backends that do not
                # support pass-level signatures yet.
                self._backend.draw_packets(batch.name, packets)
            execute_backend_draw_ms += (time.perf_counter() - backend_draw_started) * 1000.0
            self._emit_render_stage(
                "execute_pass.end",
                metadata={"pass_name": batch.name, "packet_count": packet_count},
            )
        summary = {
            "execute_packet_count": int(execute_packet_count),
            "execute_pass_count": int(len(batches)),
            "execute_static_packet_count": int(execute_static_packet_count),
            "execute_dynamic_packet_count": int(execute_dynamic_packet_count),
            "execute_packet_build_ms": float(max(0.0, execute_packet_build_ms)),
            "execute_auto_static_ms": float(max(0.0, execute_auto_static_ms)),
            "execute_static_packet_cache_hits": int(execute_static_packet_cache_hits),
            "execute_backend_draw_ms": float(max(0.0, execute_backend_draw_ms)),
            "execute_pass_packet_counts": dict(sorted(execute_pass_packet_counts.items())),
            "execute_kind_packet_counts": dict(sorted(execute_kind_packet_counts.items())),
        }
        consume_execute_telemetry = getattr(self._backend, "consume_execute_telemetry", None)
        if callable(consume_execute_telemetry):
            payload = consume_execute_telemetry()
            if isinstance(payload, dict):
                summary.update(payload)
        return summary

    def _command_batch_signature_cached(
        self, commands: tuple[RenderCommand, ...]
    ) -> tuple[object, ...]:
        if not commands:
            return ()
        return tuple(self._command_version_token_cached(command) for command in commands)

    def _annotate_packet_static_mode(
        self,
        packet: _DrawPacket,
        *,
        override: str | None = None,
        version_token: object | None = None,
    ) -> tuple[_DrawPacket, float]:
        resolved_override = override if override is not None else _packet_static_override(packet)
        auto_static_ms = 0.0
        if resolved_override == "force_static":
            effective_static = True
        elif resolved_override == "force_dynamic":
            effective_static = False
        else:
            auto_static_started = time.perf_counter()
            effective_static = self._resolve_auto_static(packet, version_token=version_token)
            auto_static_ms = (time.perf_counter() - auto_static_started) * 1000.0
        resolved_version = version_token
        if resolved_version is None:
            resolved_version = _packet_version_token(packet)
        if resolved_version is None:
            resolved_version = (
                int(id(packet.data)),
                int(id(packet.transform)),
            )
        version_key = _version_fingerprint(resolved_version)
        cache_base = (
            str(packet.kind),
            int(packet.layer),
            str(packet.sort_key),
            version_key,
        )
        return (
            _DrawPacket(
                kind=str(packet.kind),
                layer=int(packet.layer),
                sort_key=str(packet.sort_key),
                transform=tuple(packet.transform),
                data=packet.data,
                engine_static=bool(effective_static),
                engine_version=resolved_version,
                engine_cache_base=cache_base,
            ),
            float(max(0.0, auto_static_ms)),
        )

    def _resolve_auto_static(self, packet: _DrawPacket, *, version_token: object | None = None) -> bool:
        key = _packet_key(packet)
        if key is None:
            return False
        version = version_token if version_token is not None else _packet_fingerprint(packet)
        frame = int(self._frame_index)
        state = self._auto_static_state.get(key)
        if state is None:
            self._auto_static_state[key] = (version, 1, frame)
            return False
        prev_version, stable_count, _last_seen = state
        if prev_version == version:
            stable_count = int(stable_count) + 1
        else:
            stable_count = 1
        self._auto_static_state[key] = (version, stable_count, frame)
        if frame % 120 == 0:
            self._prune_auto_static_state(frame)
        return stable_count >= int(self._auto_static_min_stable_frames)

    def _command_to_packet_cached(self, command: RenderCommand) -> tuple[_DrawPacket, str, object]:
        command_id = int(id(command))
        cached = self._command_packet_cache.get(command_id)
        if cached is not None:
            cached_command, packet, override, version_token = cached
            if cached_command is command:
                return packet, override, version_token
        override = _command_static_override(command)
        packet = _command_to_packet(command)
        version_token = self._command_version_token_cached(command)
        self._command_packet_cache[command_id] = (command, packet, override, version_token)
        if len(self._command_packet_cache) > 20000:
            self._command_packet_cache.clear()
            self._command_packet_cache[command_id] = (command, packet, override, version_token)
        return packet, override, version_token

    def _command_version_token_cached(self, command: RenderCommand) -> object:
        command_id = int(id(command))
        cached = self._command_version_token_cache.get(command_id)
        if cached is not None and cached[0] is command:
            return cached[1]
        token = _command_version_token(command)
        self._command_version_token_cache[command_id] = (command, token)
        if len(self._command_version_token_cache) > 20000:
            self._command_version_token_cache.clear()
            self._command_version_token_cache[command_id] = (command, token)
        return token

    def _prune_auto_static_state(self, frame: int) -> None:
        cutoff = int(frame) - 300
        stale_keys = [key for key, (_, _, seen) in self._auto_static_state.items() if int(seen) < cutoff]
        for key in stale_keys:
            self._auto_static_state.pop(key, None)

    def _emit_render_stage(
        self,
        stage: str,
        *,
        value: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        if not self._diag_stage_events_enabled:
            return
        if self._diag_stage_sampling_n > 1 and (self._frame_index % self._diag_stage_sampling_n) != 0:
            return
        hub.emit_fast(
            category="render",
            name=f"render.stage.{stage}",
            tick=self._frame_index,
            value=value,
            metadata=metadata,
        )

    def _emit_render_frame_ms(self, value_ms: float) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        hub.emit_fast(
            category="render",
            name="render.frame_ms",
            tick=self._frame_index,
            value=float(max(0.0, value_ms)),
        )

    def _emit_render_profile_frame(
        self,
        *,
        batch_count: int,
        build_ms: float,
        execute_ms: float,
        present_ms: float,
        total_ms: float,
        mem_before_mb: float | None,
        mem_after_mb: float | None,
        execute_summary: dict[str, object] | None = None,
    ) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        if self._diag_profile_sampling_n > 1 and (self._frame_index % self._diag_profile_sampling_n) != 0:
            return
        mem_delta = None
        if mem_before_mb is not None and mem_after_mb is not None:
            mem_delta = float(mem_after_mb - mem_before_mb)
        value: dict[str, object] = {
            "batch_count": int(batch_count),
            "build_ms": float(max(0.0, build_ms)),
            "execute_ms": float(max(0.0, execute_ms)),
            "present_ms": float(max(0.0, present_ms)),
            "total_ms": float(max(0.0, total_ms)),
        }
        if mem_delta is not None:
            value["mem_delta_mb"] = mem_delta
        if execute_summary:
            value.update(execute_summary)
        resize_telemetry = self._backend.resize_telemetry()
        value.update(
            {
                "acquire_failures": _as_int(resize_telemetry.get("acquire_failures", 0)),
                "present_failures": _as_int(resize_telemetry.get("present_failures", 0)),
                "reconfigure_failures": _as_int(resize_telemetry.get("reconfigure_failures", 0)),
                "recovery_backoff_events": _as_int(
                    resize_telemetry.get("recovery_backoff_events", 0)
                ),
                "adaptive_present_mode_switches": _as_int(
                    resize_telemetry.get("adaptive_present_mode_switches", 0)
                ),
            }
        )
        hub.emit_fast(
            category="render",
            name="render.profile_frame",
            tick=self._frame_index,
            value=value,
        )

    @staticmethod
    def _traced_memory_mb() -> float | None:
        if not tracemalloc.is_tracing():
            return None
        current, _peak = tracemalloc.get_traced_memory()
        return float(current) / (1024.0 * 1024.0)

    def _assert_owner_thread(self) -> None:
        if int(threading.get_ident()) != self._owner_thread_id:
            raise RuntimeError("WgpuRenderer must run on its owner thread")

    def _emit_resize_diagnostics(
        self,
        event: WindowResizeEvent,
        telemetry: dict[str, object],
    ) -> None:
        hub = self._diagnostics_hub
        if hub is None:
            return
        tick = int(self._frame_index)
        hub.emit_fast(
            category="render",
            name="render.resize_event",
            tick=tick,
            value={
                "logical_width": float(event.logical_width),
                "logical_height": float(event.logical_height),
                "physical_width": int(event.physical_width),
                "physical_height": int(event.physical_height),
                "dpi_scale": float(event.dpi_scale),
                "viewport_revision": int(self._viewport_revision),
            },
            metadata={"source": "window_event"},
        )
        hub.emit_fast(
            category="render",
            name="render.viewport_applied",
            tick=tick,
            value={
                "width": int(self.width),
                "height": int(self.height),
                "revision": int(self._viewport_revision),
                "projection": tuple(float(v) for v in self._projection),
            },
        )
        hub.emit_fast(
            category="render",
            name="render.surface_reconfigure",
            tick=tick,
            value=telemetry,
            metadata={"reason": "resize"},
        )


def _command_key(command: RenderCommand) -> str:
    raw_key: object | None = None
    for key, value in command.data:
        if str(key) == "key":
            raw_key = value
            break
    if not isinstance(raw_key, str):
        return ""
    normalized = raw_key.strip()
    if not normalized:
        return ""
    return f"{command.kind}:{normalized}"


def _resolve_pass_descriptor(name: str) -> _PassDescriptor:
    normalized = name.strip().lower()
    if normalized in {"world", "geometry", "main"}:
        return _PassDescriptor(canonical_name="world", priority=0)
    if normalized in {"overlay", "ui", "hud"}:
        return _PassDescriptor(canonical_name="overlay", priority=1)
    if normalized.startswith("post"):
        return _PassDescriptor(canonical_name=normalized, priority=2)
    return _PassDescriptor(canonical_name=normalized or "overlay", priority=1)


def _command_to_packet(command: RenderCommand) -> _DrawPacket:
    payload = _normalized_payload(command.data)
    srgb_rgba = _extract_srgb_rgba(payload)
    linear_rgba = _srgb_to_linear_rgba_cached(srgb_rgba)
    srgb_secondary_rgba = _extract_srgb_secondary_rgba(payload, default=srgb_rgba)
    linear_secondary_rgba = _srgb_to_linear_rgba_cached(srgb_secondary_rgba)
    return _DrawPacket(
        kind=str(command.kind),
        layer=int(command.layer),
        sort_key=str(command.sort_key),
        transform=_transform_values_tuple(command.transform.values),
        data=payload
        + (
            ("srgb_rgba", srgb_rgba),
            ("linear_rgba", linear_rgba),
            ("srgb_secondary_rgba", srgb_secondary_rgba),
            ("linear_secondary_rgba", linear_secondary_rgba),
        ),
    )


def _create_wgpu_backend(
    surface: SurfaceHandle | None, *, runtime_config: RuntimeConfig | None = None
) -> _Backend:
    return _WgpuBackend(surface=surface, runtime_config=runtime_config)


def _command_sort_key(command: RenderCommand, ordinal: int) -> tuple[object, ...]:
    return (
        int(command.layer),
        str(command.sort_key),
        str(command.kind),
        _command_key(command),
        int(ordinal),
    )


def _command_static_override(command: RenderCommand) -> str:
    override_raw: object | None = None
    for key, value in command.data:
        if str(key) == "static":
            override_raw = value
            break
    if isinstance(override_raw, bool):
        return "force_static" if override_raw else "auto"
    if isinstance(override_raw, (int, float)):
        return "force_static" if bool(override_raw) else "auto"
    if isinstance(override_raw, str):
        value = override_raw.strip().lower()
        if value in {"1", "true", "yes", "on", "static", "force_static"}:
            return "force_static"
        if value in {"dynamic", "force_dynamic", "0", "false", "off"}:
            return "force_dynamic"
    return "auto"


def _command_version_token(command: RenderCommand) -> object:
    payload = tuple(command.data)
    payload_token: object
    try:
        payload_token = ("h", hash(payload), len(payload))
    except Exception:
        payload_token = ("id", int(id(payload)), len(payload))
    transform_values = _transform_values_tuple(command.transform.values)
    transform_token: object
    try:
        transform_token = ("h", hash(transform_values), len(transform_values))
    except Exception:
        transform_token = ("id", int(id(transform_values)), len(transform_values))
    return (
        str(command.kind),
        int(command.layer),
        str(command.sort_key),
        _command_key(command),
        payload_token,
        transform_token,
    )


def _normalized_payload(data: tuple[tuple[str, object], ...]) -> tuple[tuple[str, object], ...]:
    all_str = True
    for item in data:
        if not (isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)):
            all_str = False
            break
    if all_str:
        return data
    return tuple((str(key), value) for key, value in data)


def _transform_values_tuple(values: object) -> tuple[float, ...]:
    key = int(id(values))
    cached = _TRANSFORM_VALUES_CACHE.get(key)
    if cached is not None and cached[0] is values:
        return cached[1]
    try:
        raw_values = tuple(cast(Any, values))
    except TypeError:
        return ()
    out = tuple(float(value) for value in raw_values)
    _TRANSFORM_VALUES_CACHE[key] = (values, out)
    if len(_TRANSFORM_VALUES_CACHE) > _TRANSFORM_CACHE_MAX:
        _TRANSFORM_VALUES_CACHE.clear()
        _TRANSFORM_VALUES_CACHE[key] = (values, out)
    return out


def _stable_sort_value(value: object) -> object:
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return repr(value)


def _extract_srgb_rgba(payload: tuple[tuple[str, object], ...]) -> tuple[float, float, float, float]:
    color_value: object = "#ffffff"
    for key, value in payload:
        if str(key) == "color":
            color_value = value
            break
    cached = _COMMAND_COLOR_CACHE.get(color_value)
    if cached is not None:
        return cached
    if isinstance(color_value, str):
        parsed = _parse_hex_color(color_value)
        if parsed is not None:
            _COMMAND_COLOR_CACHE[color_value] = parsed
            if len(_COMMAND_COLOR_CACHE) > _COLOR_CACHE_MAX:
                _COMMAND_COLOR_CACHE.clear()
                _COMMAND_COLOR_CACHE[color_value] = parsed
            return parsed
    fallback = (1.0, 1.0, 1.0, 1.0)
    _COMMAND_COLOR_CACHE[color_value] = fallback
    if len(_COMMAND_COLOR_CACHE) > _COLOR_CACHE_MAX:
        _COMMAND_COLOR_CACHE.clear()
        _COMMAND_COLOR_CACHE[color_value] = fallback
    return fallback


def _extract_srgb_secondary_rgba(
    payload: tuple[tuple[str, object], ...],
    *,
    default: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    color_value: object | None = None
    for key, value in payload:
        if str(key) == "color_secondary":
            color_value = value
            break
    if isinstance(color_value, str):
        cached = _COMMAND_COLOR_CACHE.get(color_value)
        if cached is not None:
            return cached
        parsed = _parse_hex_color(color_value)
        if parsed is not None:
            _COMMAND_COLOR_CACHE[color_value] = parsed
            if len(_COMMAND_COLOR_CACHE) > _COLOR_CACHE_MAX:
                _COMMAND_COLOR_CACHE.clear()
                _COMMAND_COLOR_CACHE[color_value] = parsed
            return parsed
    return default


def _parse_hex_color(raw: str) -> tuple[float, float, float, float] | None:
    normalized = raw.strip().lower()
    if not normalized.startswith("#"):
        return None
    value = normalized.removeprefix("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    elif len(value) == 4:
        value = "".join(ch * 2 for ch in value)
    elif len(value) == 6:
        value = f"{value}ff"
    if len(value) != 8:
        return None
    try:
        channels = tuple(int(value[index:index + 2], 16) for index in range(0, 8, 2))
    except ValueError:
        return None
    return (
        float(channels[0]) / 255.0,
        float(channels[1]) / 255.0,
        float(channels[2]) / 255.0,
        float(channels[3]) / 255.0,
    )


def _srgb_to_linear_rgba(srgb: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    r, g, b, a = srgb
    return (_srgb_to_linear_channel(r), _srgb_to_linear_channel(g), _srgb_to_linear_channel(b), a)


def _srgb_to_linear_rgba_cached(
    srgb: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    cached = _COMMAND_LINEAR_COLOR_CACHE.get(srgb)
    if cached is not None:
        return cached
    linear = _srgb_to_linear_rgba(srgb)
    _COMMAND_LINEAR_COLOR_CACHE[srgb] = linear
    if len(_COMMAND_LINEAR_COLOR_CACHE) > _COLOR_CACHE_MAX:
        _COMMAND_LINEAR_COLOR_CACHE.clear()
        _COMMAND_LINEAR_COLOR_CACHE[srgb] = linear
    return linear


def _srgb_to_linear_channel(value: float) -> float:
    clamped = min(1.0, max(0.0, float(value)))
    if clamped <= 0.04045:
        return clamped / 12.92
    return float(((clamped + 0.055) / 1.055) ** 2.4)


def _normalize_rgba(value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, tuple) or len(value) < 4:
        return (1.0, 1.0, 1.0, 1.0)
    rgba: list[float] = []
    for channel in value[:4]:
        if isinstance(channel, (int, float)):
            rgba.append(min(1.0, max(0.0, float(channel))))
        else:
            rgba.append(1.0)
    return (rgba[0], rgba[1], rgba[2], rgba[3])


def _snap_to_pixel(value: float) -> float:
    return float(round(float(value)))


def _stroke_px(thickness_design: float, axis_scale: float) -> float:
    t = max(1.0, float(thickness_design) * max(0.01, abs(float(axis_scale))))
    return float(max(1, int(round(t))))


def _rounded_rect_draw_rects(
    *,
    layer: int,
    x: float,
    y: float,
    w: float,
    h: float,
    radius: float,
    color: tuple[float, float, float, float],
    max_steps: int = 32,
) -> tuple[_DrawRect, ...]:
    x0 = _snap_to_pixel(x)
    y0 = _snap_to_pixel(y)
    rw = max(1.0, _snap_to_pixel(w))
    rh = max(1.0, _snap_to_pixel(h))
    r = min(max(0.0, float(radius)), rw * 0.5, rh * 0.5)
    if r < 1.0:
        return (
            _DrawRect(
                layer=layer,
                x=x0,
                y=y0,
                w=rw,
                h=rh,
                color=color,
            ),
        )
    rows = max(1, min(max(1, int(max_steps)), int(round(r))))
    out: list[_DrawRect] = []
    mid_h = max(0.0, rh - (2.0 * float(rows)))
    if mid_h > 0.0:
        out.append(
            _DrawRect(
                layer=layer,
                x=x0,
                y=y0 + float(rows),
                w=rw,
                h=mid_h,
                color=color,
            )
        )
    for i in range(rows):
        # Distance from top-corner center; larger at top rows, smaller toward the body.
        dy = min(float(rows) - 0.0001, float(rows) - (float(i) + 0.5))
        inset = max(
            0.0,
            float(rows) - ((max(0.0, (float(rows) * float(rows)) - (dy * dy))) ** 0.5),
        )
        seg_w = max(1.0, rw - (2.0 * inset))
        sx = x0 + inset
        ty = y0 + float(i)
        by = y0 + rh - float(i) - 1.0
        out.append(
            _DrawRect(
                layer=layer,
                x=sx,
                y=ty,
                w=seg_w,
                h=1.0,
                color=color,
            )
        )
        out.append(
            _DrawRect(
                layer=layer,
                x=sx,
                y=by,
                w=seg_w,
                h=1.0,
                color=color,
            )
        )
    return tuple(out)


def _lerp(a: float, b: float, t: float) -> float:
    return float(a) + ((float(b) - float(a)) * float(t))


def _packet_payload(packet: _DrawPacket) -> dict[str, object]:
    raw_data = getattr(packet, "data", ())
    payload: dict[str, object] = {}
    if not isinstance(raw_data, tuple):
        return payload
    for item in raw_data:
        if isinstance(item, tuple) and len(item) == 2:
            payload[str(item[0])] = item[1]
    return payload


def _try_create_freetype_face(font_path: str) -> object | None:
    if not font_path:
        return None
    try:
        import freetype

        return cast(object, freetype.Face(font_path))
    except Exception:
        return None


def _load_font_blob(font_path: str) -> bytes | None:
    if not font_path:
        return None
    try:
        with open(font_path, "rb") as handle:
            return handle.read()
    except Exception:
        return None


def _rasterize_glyph_bitmap(
    *,
    face: object | None,
    character: str,
    size_px: int,
) -> tuple[int, int, int, int, float, bytes] | None:
    if face is None or not character:
        return None
    try:
        set_pixel_sizes = getattr(face, "set_pixel_sizes", None)
        load_char = getattr(face, "load_char", None)
        glyph = getattr(face, "glyph", None)
        if not callable(set_pixel_sizes) or not callable(load_char) or glyph is None:
            return None
        set_pixel_sizes(0, int(max(1, size_px)))
        load_char(character)
        bitmap = getattr(glyph, "bitmap", None)
        if bitmap is None:
            return None
        width = int(getattr(bitmap, "width", 0))
        rows = int(getattr(bitmap, "rows", 0))
        pitch = int(getattr(bitmap, "pitch", width))
        left = int(getattr(glyph, "bitmap_left", 0))
        top = int(getattr(glyph, "bitmap_top", 0))
        advance_raw = getattr(getattr(glyph, "advance", None), "x", 0)
        advance = float(float(advance_raw) / 64.0) if isinstance(advance_raw, (int, float)) else 0.0
        if width <= 0 or rows <= 0:
            return (0, 0, left, top, max(advance, float(size_px) * 0.3), b"")
        buffer_obj = getattr(bitmap, "buffer", b"")
        raw = bytes(buffer_obj)
        if pitch == width:
            alpha = raw[: width * rows]
        else:
            out = bytearray()
            row_pitch = max(width, abs(pitch))
            for row in range(rows):
                if pitch >= 0:
                    start = row * row_pitch
                else:
                    start = (rows - 1 - row) * row_pitch
                out.extend(raw[start : start + width])
            alpha = bytes(out)
        return (width, rows, left, top, max(advance, float(width)), alpha)
    except Exception:
        return None


def _rasterize_glyph_index_bitmap(
    *,
    face: object | None,
    glyph_index: int,
    size_px: int,
) -> tuple[int, int, int, int, float, bytes] | None:
    if face is None:
        return None
    try:
        set_pixel_sizes = getattr(face, "set_pixel_sizes", None)
        load_glyph = getattr(face, "load_glyph", None)
        glyph = getattr(face, "glyph", None)
        if not callable(set_pixel_sizes) or not callable(load_glyph) or glyph is None:
            return None
        set_pixel_sizes(0, int(max(1, size_px)))
        load_glyph(int(max(0, glyph_index)))
        bitmap = getattr(glyph, "bitmap", None)
        if bitmap is None:
            return None
        width = int(getattr(bitmap, "width", 0))
        rows = int(getattr(bitmap, "rows", 0))
        pitch = int(getattr(bitmap, "pitch", width))
        left = int(getattr(glyph, "bitmap_left", 0))
        top = int(getattr(glyph, "bitmap_top", 0))
        advance_raw = getattr(getattr(glyph, "advance", None), "x", 0)
        advance = float(float(advance_raw) / 64.0) if isinstance(advance_raw, (int, float)) else 0.0
        if width <= 0 or rows <= 0:
            return (0, 0, left, top, max(advance, float(size_px) * 0.3), b"")
        buffer_obj = getattr(bitmap, "buffer", b"")
        raw = bytes(buffer_obj)
        if pitch == width:
            alpha = raw[: width * rows]
        else:
            out = bytearray()
            row_pitch = max(width, abs(pitch))
            for row in range(rows):
                if pitch >= 0:
                    start = row * row_pitch
                else:
                    start = (rows - 1 - row) * row_pitch
                out.extend(raw[start : start + width])
            alpha = bytes(out)
        return (width, rows, left, top, max(advance, float(width)), alpha)
    except Exception:
        return None


def _payload_float(payload: dict[str, object], key: str, default: float) -> float:
    raw = payload.get(key, default)
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(default)


def _payload_int(payload: dict[str, object], key: str, default: int) -> int:
    raw = payload.get(key, default)
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float):
        return int(round(raw))
    return int(default)


def _rect_from_payload(payload: dict[str, object], *, color: tuple[float, float, float, float]) -> _DrawRect:
    return _DrawRect(
        layer=0,
        x=_payload_float(payload, "x", 0.0),
        y=_payload_float(payload, "y", 0.0),
        w=max(1.0, _payload_float(payload, "w", _payload_float(payload, "width", 1.0))),
        h=max(1.0, _payload_float(payload, "h", _payload_float(payload, "height", 1.0))),
        color=color,
    )


def _grid_draw_rects(
    payload: dict[str, object], *, color: tuple[float, float, float, float]
) -> tuple[_DrawRect, ...]:
    x = _payload_float(payload, "x", 0.0)
    y = _payload_float(payload, "y", 0.0)
    width = max(1.0, _payload_float(payload, "width", 1.0))
    height = max(1.0, _payload_float(payload, "height", 1.0))
    lines = max(2, _payload_int(payload, "lines", 2))
    divisions = max(1, lines - 1)
    thickness = max(1.0, min(width, height) / 300.0)
    max_vx = x + width - thickness
    max_hy = y + height - thickness
    rects: list[_DrawRect] = []
    for i in range(lines):
        t = float(i) / float(divisions)
        vx = min(max(x, x + (width * t) - (thickness * 0.5)), max_vx)
        hy = min(max(y, y + (height * t) - (thickness * 0.5)), max_hy)
        rects.append(
            _DrawRect(
                layer=0,
                x=vx,
                y=y,
                w=thickness,
                h=height,
                color=color,
            )
        )
        rects.append(
            _DrawRect(
                layer=0,
                x=x,
                y=hy,
                w=width,
                h=thickness,
                color=color,
            )
        )
    return tuple(rects)


def _text_draw_rects(
    payload: dict[str, object], *, color: tuple[float, float, float, float]
) -> tuple[_DrawRect, ...]:
    text_raw = payload.get("text", "")
    if not isinstance(text_raw, str):
        return ()
    text = text_raw.strip("\n")
    if not text:
        return ()
    x = _payload_float(payload, "x", 0.0)
    y = _payload_float(payload, "y", 0.0)
    font_size = max(6.0, _payload_float(payload, "font_size", 18.0))
    anchor_raw = payload.get("anchor", "top-left")
    anchor = str(anchor_raw).strip().lower() if isinstance(anchor_raw, str) else "top-left"
    pixel = float(max(1, int(round(font_size / 8.0))))
    glyph_w = 5.0 * pixel
    glyph_h = 7.0 * pixel
    advance = 6.0 * pixel
    text_w = max(glyph_w, (len(text) * advance) - pixel)
    text_h = glyph_h
    origin_x, origin_y = _anchor_to_origin(anchor, x, y, text_w, text_h)
    origin_x = float(round(origin_x))
    origin_y = float(round(origin_y))
    rects: list[_DrawRect] = []
    cursor_x = origin_x
    for ch in text:
        glyph_rows = _BITMAP_FONT_5X7.get(ch)
        if glyph_rows is None:
            glyph_rows = _BITMAP_FONT_5X7.get(ch.upper(), _BITMAP_FONT_5X7["?"])
        for row_idx, row_bits in enumerate(glyph_rows):
            py = origin_y + (float(row_idx) * pixel)
            col_idx = 0
            while col_idx < len(row_bits):
                if row_bits[col_idx] != "1":
                    col_idx += 1
                    continue
                run_start = col_idx
                while col_idx < len(row_bits) and row_bits[col_idx] == "1":
                    col_idx += 1
                run_len = col_idx - run_start
                px = cursor_x + (float(run_start) * pixel)
                rects.append(
                    _DrawRect(
                        layer=0,
                        x=px,
                        y=py,
                        w=float(run_len) * pixel,
                        h=pixel,
                        color=color,
                    )
                )
        cursor_x += advance
    return tuple(rects)


def _anchor_to_origin(anchor: str, x: float, y: float, width: float, height: float) -> tuple[float, float]:
    horizontal = "left"
    vertical = "top"
    if "-" in anchor:
        parts = [part for part in anchor.split("-") if part]
        if len(parts) >= 2:
            vertical = parts[0]
            horizontal = parts[1]
    elif anchor in {"top", "middle", "bottom"}:
        vertical = anchor
    elif anchor in {"left", "center", "right"}:
        horizontal = anchor
    ox = float(x)
    oy = float(y)
    if horizontal in {"center", "middle"}:
        ox -= width * 0.5
    elif horizontal == "right":
        ox -= width
    if vertical == "middle":
        oy -= height * 0.5
    elif vertical == "bottom":
        oy -= height
    return ox, oy


def _safe_uv_bounds(*, start_px: int, size_px: int, atlas_size_px: int) -> tuple[float, float]:
    atlas = float(max(1, int(atlas_size_px)))
    start = int(max(0, start_px))
    size = int(max(1, size_px))
    if size <= 1:
        center = (float(start) + 0.5) / atlas
        return (center, center)
    # Sample the full glyph rect in atlas space; half-texel inset can visibly
    # trim edge coverage on all sides for small/medium UI text.
    u0 = float(start) / atlas
    u1 = float(start + size) / atlas
    return (u0, u1)


_BITMAP_FONT_5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "=": ("00000", "11111", "00000", "11111", "00000", "00000", "00000"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "#": ("01010", "11111", "01010", "01010", "11111", "01010", "01010"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "00110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10000", "10011", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00001", "00001", "00001", "00001", "10001", "10001", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _geometry_wgsl_for_color(color: tuple[float, float, float, float]) -> str:
    r, g, b, a = (float(color[0]), float(color[1]), float(color[2]), float(color[3]))
    return f"""
struct VsIn {{
    @location(0) pos: vec2<f32>,
}};

@vertex
fn vs_main(input: VsIn) -> @builtin(position) vec4<f32> {{
    return vec4<f32>(input.pos, 0.0, 1.0);
}}

@fragment
fn fs_main() -> @location(0) vec4<f32> {{
    return vec4<f32>({r:.8f}, {g:.8f}, {b:.8f}, {a:.8f});
}}
"""


@dataclass(slots=True)
class _WgpuBackend:
    """Backend initialization scaffold used during migration."""

    surface: SurfaceHandle | None = None
    runtime_config: RuntimeConfig | None = None
    _title: str = field(init=False, default="")
    _wgpu_loaded: bool = field(init=False, default=False)
    _wgpu: object = field(init=False)
    _adapter: object = field(init=False)
    _device: object = field(init=False)
    _queue: object = field(init=False)
    _surface_state: dict[str, object] = field(init=False, default_factory=dict)
    _surface_format: str = field(init=False, default="bgra8unorm-srgb")
    _geometry_pipeline: object | None = field(init=False, default=None)
    _text_pipeline: object | None = field(init=False, default=None)
    _text_bind_group: object | None = field(init=False, default=None)
    _text_sampler: object | None = field(init=False, default=None)
    _text_atlas_texture: object | None = field(init=False, default=None)
    _text_atlas_view: object | None = field(init=False, default=None)
    _text_atlas_width: int = field(init=False, default=1024)
    _text_atlas_height: int = field(init=False, default=1024)
    _text_atlas_pixels: bytearray = field(init=False, default_factory=bytearray)
    _text_atlas_cursor_x: int = field(init=False, default=1)
    _text_atlas_cursor_y: int = field(init=False, default=1)
    _text_atlas_row_height: int = field(init=False, default=0)
    _text_atlas_dirty: bool = field(init=False, default=False)
    _text_face: object | None = field(init=False, default=None)
    _glyph_atlas_cache: dict[tuple[int, str], _GlyphAtlasEntry] = field(init=False, default_factory=dict)
    _glyph_index_atlas_cache: dict[tuple[int, int], _GlyphAtlasEntry] = field(
        init=False, default_factory=dict
    )
    _glyph_run_cache: dict[tuple[str, int, int, str], _GlyphRunLayout] = field(
        init=False, default_factory=dict
    )
    _hb_font_cache: dict[int, object] = field(init=False, default_factory=dict)
    _font_vertical_metrics_cache: dict[int, _FontVerticalMetrics] = field(
        init=False, default_factory=dict
    )
    _draw_text_vertex_buffer_static: object | None = field(init=False, default=None)
    _draw_text_vertex_buffer_static_capacity: int = field(init=False, default=0)
    _draw_text_vertex_buffer_dynamic: object | None = field(init=False, default=None)
    _draw_text_vertex_buffer_dynamic_capacity: int = field(init=False, default=0)
    _static_text_cache_key: tuple[object, ...] | None = field(init=False, default=None)
    _static_text_vertex_count: int = field(init=False, default=0)
    _static_text_bundle: object | None = field(init=False, default=None)
    _static_text_bundle_key: tuple[object, ...] | None = field(init=False, default=None)
    _frame_texture: object | None = field(init=False, default=None)
    _frame_texture_view: object | None = field(init=False, default=None)
    _frame_color_view: object | None = field(init=False, default=None)
    _command_encoder: object | None = field(init=False, default=None)
    _queued_packets: list[tuple[str, tuple[_DrawPacket, ...]]] = field(init=False, default_factory=list)
    _target_width: int = field(init=False, default=1200)
    _target_height: int = field(init=False, default=720)
    _window_width: int = field(init=False, default=1200)
    _window_height: int = field(init=False, default=720)
    _internal_render_scale: float = field(init=False, default=1.0)
    _upload_threshold_packets: int = field(init=False, default=256)
    _static_bundle_min_draw_calls: int = field(init=False, default=2)
    _static_pass_expand_cache_max: int = field(init=False, default=512)
    _upload_mode_last: str = field(init=False, default="none")
    _uploaded_packet_count: int = field(init=False, default=0)
    _stream_write_cursor: int = field(init=False, default=0)
    _upload_stream_buffer: object | None = field(init=False, default=None)
    _upload_stream_buffer_capacity: int = field(init=False, default=0)
    _draw_vertex_buffer_static: object | None = field(init=False, default=None)
    _draw_vertex_buffer_static_capacity: int = field(init=False, default=0)
    _draw_vertex_buffer_dynamic: object | None = field(init=False, default=None)
    _draw_vertex_buffer_dynamic_capacity: int = field(init=False, default=0)
    _static_draw_cache_key: tuple[object, ...] | None = field(init=False, default=None)
    _static_draw_runs: tuple[tuple[int, int], ...] = field(
        init=False, default_factory=tuple
    )
    _static_render_bundle: object | None = field(init=False, default=None)
    _static_render_bundle_key: tuple[object, ...] | None = field(init=False, default=None)
    _execute_static_reused_frame: bool = field(init=False, default=False)
    _execute_static_bundle_replayed_frame: bool = field(init=False, default=False)
    _execute_static_upload_bytes_frame: int = field(init=False, default=0)
    _execute_dynamic_upload_bytes_frame: int = field(init=False, default=0)
    _execute_static_rebuild_count_frame: int = field(init=False, default=0)
    _execute_static_run_count_frame: int = field(init=False, default=0)
    _execute_dynamic_run_count_frame: int = field(init=False, default=0)
    _execute_stage_upload_ms_frame: float = field(init=False, default=0.0)
    _execute_translate_ms_frame: float = field(init=False, default=0.0)
    _execute_expand_ms_frame: float = field(init=False, default=0.0)
    _execute_draw_packets_total_ms_frame: float = field(init=False, default=0.0)
    _execute_packet_preprocess_ms_frame: float = field(init=False, default=0.0)
    _execute_static_key_build_ms_frame: float = field(init=False, default=0.0)
    _execute_begin_render_pass_ms_frame: float = field(init=False, default=0.0)
    _execute_render_pass_record_ms_frame: float = field(init=False, default=0.0)
    _execute_render_pass_end_ms_frame: float = field(init=False, default=0.0)
    _execute_rect_batch_ms_frame: float = field(init=False, default=0.0)
    _execute_text_batch_ms_frame: float = field(init=False, default=0.0)
    _execute_text_layout_ms_frame: float = field(init=False, default=0.0)
    _execute_text_shape_ms_frame: float = field(init=False, default=0.0)
    _execute_atlas_upload_ms_frame: float = field(init=False, default=0.0)
    _execute_atlas_upload_bytes_frame: int = field(init=False, default=0)
    _execute_atlas_upload_count_frame: int = field(init=False, default=0)
    _execute_packet_translate_count_frame: int = field(init=False, default=0)
    _execute_rect_count_frame: int = field(init=False, default=0)
    _execute_text_quad_count_frame: int = field(init=False, default=0)
    _execute_draw_calls_frame: int = field(init=False, default=0)
    _execute_pipeline_binds_frame: int = field(init=False, default=0)
    _execute_vertex_buffer_binds_frame: int = field(init=False, default=0)
    _execute_bind_group_binds_frame: int = field(init=False, default=0)
    _execute_bundle_replays_frame: int = field(init=False, default=0)
    _execute_text_shape_calls_frame: int = field(init=False, default=0)
    _execute_kind_rect_counts_frame: dict[str, int] = field(init=False, default_factory=dict)
    _execute_kind_text_quad_counts_frame: dict[str, int] = field(init=False, default_factory=dict)
    _reconfigure_retry_limit: int = field(init=False, default=2)
    _reconfigure_attempts_last: int = field(init=False, default=0)
    _reconfigure_failures: int = field(init=False, default=0)
    _device_identity: int = field(init=False, default=0)
    _adapter_identity: int = field(init=False, default=0)
    _present_mode: str = field(init=False, default="fifo")
    _selected_backend: str = field(init=False, default="unknown")
    _adapter_info: dict[str, object] = field(init=False, default_factory=dict)
    _font_path: str = field(init=False, default="")
    _font_blob: bytes | None = field(init=False, default=None)
    _frame_in_flight: bool = field(init=False, default=False)
    _frame_in_flight_limit: int = field(init=False, default=1)
    _clear_pending: bool = field(init=False, default=True)
    _canvas: object | None = field(init=False, default=None)
    _canvas_context: object | None = field(init=False, default=None)
    _geometry_shader_module: object | None = field(init=False, default=None)
    _geometry_pipeline_cache: dict[tuple[float, float, float, float], object] = field(
        init=False, default_factory=dict
    )
    _design_width: int = field(init=False, default=1200)
    _design_height: int = field(init=False, default=720)
    _preserve_aspect: bool = field(init=False, default=False)
    _acquire_attempts_last: int = field(init=False, default=0)
    _acquire_failures: int = field(init=False, default=0)
    _acquire_recoveries: int = field(init=False, default=0)
    _present_attempts_last: int = field(init=False, default=0)
    _present_failures: int = field(init=False, default=0)
    _present_recoveries: int = field(init=False, default=0)
    _last_present_error: str = field(init=False, default="")
    _acquire_failure_streak: int = field(init=False, default=0)
    _present_failure_streak: int = field(init=False, default=0)
    _recovery_backoff_until_s: float = field(init=False, default=0.0)
    _recovery_backoff_events: int = field(init=False, default=0)
    _adaptive_present_mode_switches: int = field(init=False, default=0)
    _recovery_failure_streak_threshold: int = field(init=False, default=3)
    _recovery_cooldown_s: float = field(init=False, default=0.05)
    _reconfigure_retry_limit_max: int = field(init=False, default=4)
    _vsync_enabled: bool = field(init=False, default=True)
    _present_mode_supported: tuple[str, ...] = field(init=False, default=("fifo", "mailbox", "immediate"))
    _static_packet_rect_cache: dict[tuple[object, ...], tuple[_DrawRect, ...]] = field(
        init=False, default_factory=dict
    )
    _static_packet_text_quad_cache: dict[tuple[object, ...], tuple[_DrawTextQuad, ...]] = field(
        init=False, default_factory=dict
    )
    _static_pass_expand_cache: dict[
        tuple[str, tuple[object, ...], tuple[object, ...]],
        _StaticPassExpandCacheEntry,
    ] = field(init=False, default_factory=dict)
    _cffi_miss_diagnostics_enabled: bool = field(init=False, default=False)
    _cffi_miss_store: dict[str, int] | None = field(init=False, default=None)
    _cffi_miss_total_last: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        runtime_config = self.runtime_config or get_runtime_config()
        if self.runtime_config is not None:
            set_runtime_config(runtime_config)
        self._preserve_aspect = resolve_preserve_aspect(runtime_config)
        design_w, design_h = _resolve_ui_design_dimensions(
            default_width=int(_DEFAULT_UI_DESIGN_WIDTH),
            default_height=int(_DEFAULT_UI_DESIGN_HEIGHT),
            runtime_config=runtime_config,
        )
        self._design_width = int(design_w)
        self._design_height = int(design_h)
        self._internal_render_scale = float(runtime_config.renderer.internal_scale)
        self._cffi_miss_diagnostics_enabled = bool(
            runtime_config.renderer.cffi_miss_diagnostics_enabled
        )
        if _NP is None:
            raise WgpuInitError(
                "wgpu backend initialization failed",
                details={
                    "selected_backend": self._selected_backend,
                    "adapter_info": dict(self._adapter_info),
                    "missing_dependency": "numpy",
                    "requirement": "Phase 9 native render-prep path requires numpy",
                },
            )
        if _HB is None:
            raise WgpuInitError(
                "wgpu backend initialization failed",
                details={
                    "selected_backend": self._selected_backend,
                    "adapter_info": dict(self._adapter_info),
                    "missing_dependency": "uharfbuzz",
                    "requirement": "Phase 9 native text shaping path requires uharfbuzz",
                },
            )
        self._recovery_failure_streak_threshold = max(
            1, int(runtime_config.renderer.recovery_failure_streak_threshold)
        )
        self._recovery_cooldown_s = (
            max(0.0, float(runtime_config.renderer.recovery_cooldown_ms)) / 1000.0
        )
        self._reconfigure_retry_limit_max = max(
            max(2, int(self._reconfigure_retry_limit)),
            int(runtime_config.renderer.recovery_max_retry_limit),
        )
        self._window_width = int(max(1, self._target_width))
        self._window_height = int(max(1, self._target_height))
        self._target_width, self._target_height = self._resolve_internal_render_size(
            self._window_width,
            self._window_height,
        )
        self._static_bundle_min_draw_calls = max(
            1, int(runtime_config.renderer.static_bundle_min_draws)
        )
        self._static_pass_expand_cache_max = max(
            64, int(runtime_config.renderer.static_pass_expand_cache_max)
        )
        try:
            import wgpu
        except Exception as exc:
            raise WgpuInitError(
                "wgpu dependency unavailable",
                details={
                    "selected_backend": "unknown",
                    "adapter_info": {},
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                },
            ) from exc
        self._wgpu = wgpu
        _patch_wgpu_native_struct_alloc_fastpath()
        _prewarm_wgpu_native_cffi_types()
        if self._cffi_miss_diagnostics_enabled:
            self._cffi_miss_store = _resolve_wgpu_native_cffi_miss_store()
            if self._cffi_miss_store:
                self._cffi_miss_total_last = int(sum(int(v) for v in self._cffi_miss_store.values()))
        try:
            self._adapter, self._selected_backend = self._request_adapter()
            self._adapter_info = self._extract_adapter_info(self._adapter)
            self._device = self._request_device(self._adapter)
            self._font_path = _resolve_system_font_path(runtime_config=runtime_config)
        except Exception as exc:
            details: dict[str, object] = {
                "selected_backend": self._selected_backend,
                "adapter_info": dict(self._adapter_info),
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            }
            if isinstance(exc, WgpuInitError):
                details.update(exc.details)
            raise WgpuInitError("wgpu backend initialization failed", details=details) from exc
        self._adapter_identity = id(self._adapter)
        self._device_identity = id(self._device)
        self._queue = getattr(self._device, "queue", None)
        if self._queue is None:
            raise RuntimeError("wgpu device queue unavailable")
        self._surface_state = self._setup_surface_state()
        self._init_canvas_surface_context()
        self._setup_pipelines()
        if not self._supports_text_atlas():
            raise WgpuInitError(
                "wgpu text atlas initialization failed",
                details={
                    "selected_backend": self._selected_backend,
                    "adapter_info": dict(self._adapter_info),
                    "font_path": str(self._font_path),
                    "text_pipeline_ready": bool(self._text_pipeline is not None),
                    "text_bind_group_ready": bool(self._text_bind_group is not None),
                    "text_atlas_texture_ready": bool(self._text_atlas_texture is not None),
                    "text_face_ready": bool(self._text_face is not None),
                },
            )
        self._rebuild_frame_targets()
        self._prime_native_paths()
        self._prime_text_paths()
        self._prime_startup_render_paths()
        self._wgpu_loaded = True

    def begin_frame(self) -> None:
        if self._frame_in_flight:
            raise RuntimeError("wgpu backend supports only one frame in flight")
        self._frame_in_flight = True
        create_command_encoder = getattr(self._device, "create_command_encoder", None)
        if callable(create_command_encoder):
            self._command_encoder = create_command_encoder(label="engine.wgpu.frame")
        else:
            self._command_encoder = SimpleNamespace()
        self._frame_color_view = self._acquire_frame_color_view()
        self._clear_pending = True
        self._queued_packets.clear()
        self._execute_static_reused_frame = False
        self._execute_static_bundle_replayed_frame = False
        self._execute_static_upload_bytes_frame = 0
        self._execute_dynamic_upload_bytes_frame = 0
        self._execute_static_rebuild_count_frame = 0
        self._execute_static_run_count_frame = 0
        self._execute_dynamic_run_count_frame = 0
        self._execute_stage_upload_ms_frame = 0.0
        self._execute_translate_ms_frame = 0.0
        self._execute_expand_ms_frame = 0.0
        self._execute_draw_packets_total_ms_frame = 0.0
        self._execute_packet_preprocess_ms_frame = 0.0
        self._execute_static_key_build_ms_frame = 0.0
        self._execute_begin_render_pass_ms_frame = 0.0
        self._execute_render_pass_record_ms_frame = 0.0
        self._execute_render_pass_end_ms_frame = 0.0
        self._execute_rect_batch_ms_frame = 0.0
        self._execute_text_batch_ms_frame = 0.0
        self._execute_text_layout_ms_frame = 0.0
        self._execute_text_shape_ms_frame = 0.0
        self._execute_atlas_upload_ms_frame = 0.0
        self._execute_atlas_upload_bytes_frame = 0
        self._execute_atlas_upload_count_frame = 0
        self._execute_packet_translate_count_frame = 0
        self._execute_rect_count_frame = 0
        self._execute_text_quad_count_frame = 0
        self._execute_draw_calls_frame = 0
        self._execute_pipeline_binds_frame = 0
        self._execute_vertex_buffer_binds_frame = 0
        self._execute_bind_group_binds_frame = 0
        self._execute_bundle_replays_frame = 0
        self._execute_text_shape_calls_frame = 0
        self._execute_kind_rect_counts_frame.clear()
        self._execute_kind_text_quad_counts_frame.clear()

    def draw_packets(
        self,
        pass_name: str,
        packets: tuple[_DrawPacket, ...],
        *,
        pass_signature: tuple[object, ...] | None = None,
    ) -> None:
        draw_packets_started = time.perf_counter()
        self._queued_packets.append((str(pass_name), packets))
        self._stage_draw_packets(packets)
        encoder = self._command_encoder
        if encoder is None:
            return
        begin_render_pass = getattr(encoder, "begin_render_pass", None)
        if not callable(begin_render_pass):
            return
        target_view = self._frame_color_view or self._frame_texture_view
        if target_view is None:
            return
        static_draw_rects: list[_DrawRect] = []
        dynamic_draw_rects: list[_DrawRect] = []
        static_text_quads: list[_DrawTextQuad] = []
        dynamic_text_quads: list[_DrawTextQuad] = []
        static_draw_packet_keys: list[tuple[object, ...]] = []
        static_text_packet_keys: list[tuple[object, ...]] = []
        supports_text_atlas = self._supports_text_atlas()
        sx, sy, ox, oy = viewport_transform(
            width=max(1, int(self._target_width)),
            height=max(1, int(self._target_height)),
            design_width=max(1, int(self._design_width)),
            design_height=max(1, int(self._design_height)),
            preserve_aspect=bool(self._preserve_aspect),
        )
        viewport_cache_key = (
            float(sx),
            float(sy),
            float(ox),
            float(oy),
            int(self._target_width),
            int(self._target_height),
            int(self._design_width),
            int(self._design_height),
            bool(self._preserve_aspect),
        )
        static_expand_cache_key: tuple[str, tuple[object, ...], tuple[object, ...]] | None = None
        cached_static_entry: _StaticPassExpandCacheEntry | None = None
        current_static_identity: tuple[tuple[object, ...], ...] = tuple(
            _static_packet_identity(packet) for packet in packets if _packet_is_static(packet)
        )
        if pass_signature is not None:
            static_expand_cache_key = (str(pass_name), tuple(pass_signature), viewport_cache_key)
            candidate = self._static_pass_expand_cache.get(static_expand_cache_key)
            if (
                candidate is not None
                and candidate.static_packet_identity == current_static_identity
            ):
                cached_static_entry = candidate
        if cached_static_entry is not None:
            static_draw_rects.extend(cached_static_entry.static_draw_rects)
            static_text_quads.extend(cached_static_entry.static_text_quads)
            static_draw_packet_keys.extend(cached_static_entry.static_draw_packet_keys)
            static_text_packet_keys.extend(cached_static_entry.static_text_packet_keys)
            self._execute_rect_count_frame += int(cached_static_entry.rect_count)
            self._execute_text_quad_count_frame += int(cached_static_entry.text_quad_count)
            self._execute_packet_translate_count_frame += int(
                cached_static_entry.packet_translate_count
            )
            for kind, count in cached_static_entry.kind_rect_counts:
                self._execute_kind_rect_counts_frame[kind] = (
                    int(self._execute_kind_rect_counts_frame.get(kind, 0)) + int(count)
                )
            for kind, count in cached_static_entry.kind_text_quad_counts:
                self._execute_kind_text_quad_counts_frame[kind] = (
                    int(self._execute_kind_text_quad_counts_frame.get(kind, 0)) + int(count)
                )
        preprocess_started = time.perf_counter()
        static_kind_rect_counts: dict[str, int] = {}
        static_kind_text_counts: dict[str, int] = {}
        static_rect_count = 0
        static_text_quad_count = 0
        static_packet_translate_count = 0
        for packet in packets:
            kind_name = str(getattr(packet, "kind", "")) or "unknown"
            packet_is_static = _packet_is_static(packet)
            if packet_is_static and cached_static_entry is not None:
                continue
            static_packet_key: tuple[object, ...] | None = None
            if packet_is_static:
                static_key_started = time.perf_counter()
                static_packet_key = self._build_static_packet_cache_key(
                    packet,
                    sx=sx,
                    sy=sy,
                    ox=ox,
                    oy=oy,
                    viewport_cache_key=viewport_cache_key,
                )
                self._execute_static_key_build_ms_frame += (
                    time.perf_counter() - static_key_started
                ) * 1000.0
            self._execute_packet_translate_count_frame += 1
            if packet_is_static:
                static_packet_translate_count += 1
            if str(packet.kind) == "text" and supports_text_atlas:
                text_started = time.perf_counter()
                text_quads = self._packet_text_quads(
                    packet,
                    sx=sx,
                    sy=sy,
                    ox=ox,
                    oy=oy,
                    static_cache_key=static_packet_key,
                    viewport_cache_key=viewport_cache_key,
                )
                self._execute_translate_ms_frame += (time.perf_counter() - text_started) * 1000.0
                if text_quads:
                    self._execute_text_quad_count_frame += int(len(text_quads))
                    self._execute_kind_text_quad_counts_frame[kind_name] = (
                        int(self._execute_kind_text_quad_counts_frame.get(kind_name, 0))
                        + int(len(text_quads))
                    )
                    if packet_is_static:
                        static_text_quad_count += int(len(text_quads))
                        static_kind_text_counts[kind_name] = (
                            int(static_kind_text_counts.get(kind_name, 0)) + int(len(text_quads))
                        )
                        static_text_quads.extend(text_quads)
                        if static_packet_key is not None:
                            static_text_packet_keys.append(static_packet_key)
                    else:
                        dynamic_text_quads.extend(text_quads)
                    continue
            rect_started = time.perf_counter()
            packet_rects = self._packet_draw_rects_cached(
                packet,
                sx=sx,
                sy=sy,
                ox=ox,
                oy=oy,
                static_cache_key=static_packet_key,
                viewport_cache_key=viewport_cache_key,
            )
            elapsed_ms = (time.perf_counter() - rect_started) * 1000.0
            self._execute_translate_ms_frame += elapsed_ms
            self._execute_expand_ms_frame += elapsed_ms
            if not packet_rects:
                continue
            self._execute_rect_count_frame += int(len(packet_rects))
            self._execute_kind_rect_counts_frame[kind_name] = (
                int(self._execute_kind_rect_counts_frame.get(kind_name, 0))
                + int(len(packet_rects))
            )
            if packet_is_static:
                static_rect_count += int(len(packet_rects))
                static_kind_rect_counts[kind_name] = (
                    int(static_kind_rect_counts.get(kind_name, 0)) + int(len(packet_rects))
                )
                static_draw_rects.extend(packet_rects)
                if static_packet_key is not None:
                    static_draw_packet_keys.append(static_packet_key)
            else:
                dynamic_draw_rects.extend(packet_rects)
        self._execute_packet_preprocess_ms_frame += (time.perf_counter() - preprocess_started) * 1000.0
        if (
            cached_static_entry is None
            and static_expand_cache_key is not None
            and (static_draw_packet_keys or static_text_packet_keys)
        ):
            self._static_pass_expand_cache[static_expand_cache_key] = _StaticPassExpandCacheEntry(
                static_draw_rects=tuple(static_draw_rects),
                static_text_quads=tuple(static_text_quads),
                static_draw_packet_keys=tuple(static_draw_packet_keys),
                static_text_packet_keys=tuple(static_text_packet_keys),
                static_packet_identity=current_static_identity,
                kind_rect_counts=tuple(sorted(static_kind_rect_counts.items())),
                kind_text_quad_counts=tuple(sorted(static_kind_text_counts.items())),
                rect_count=int(static_rect_count),
                text_quad_count=int(static_text_quad_count),
                packet_translate_count=int(static_packet_translate_count),
            )
            while len(self._static_pass_expand_cache) > int(self._static_pass_expand_cache_max):
                first_key = next(iter(self._static_pass_expand_cache))
                self._static_pass_expand_cache.pop(first_key, None)
        if not static_draw_rects and not dynamic_draw_rects and not static_text_quads and not dynamic_text_quads:
            return
        color_attachments = [
            {
                "view": target_view,
                "clear_value": (0.0, 0.0, 0.0, 1.0),
                "load_op": "clear" if self._clear_pending else "load",
                "store_op": "store",
            }
        ]
        self._clear_pending = False
        render_pass_begin_started = time.perf_counter()
        render_pass = begin_render_pass(color_attachments=color_attachments)
        self._execute_begin_render_pass_ms_frame += (
            time.perf_counter() - render_pass_begin_started
        ) * 1000.0
        render_record_started = time.perf_counter()
        try:
            if static_draw_rects:
                rect_batch_started = time.perf_counter()
                self._draw_rect_batches(
                    render_pass,
                    tuple(static_draw_rects),
                    stream_kind="static",
                    static_batch_key=tuple(static_draw_packet_keys),
                )
                self._execute_rect_batch_ms_frame += (time.perf_counter() - rect_batch_started) * 1000.0
            if dynamic_draw_rects:
                rect_batch_started = time.perf_counter()
                self._draw_rect_batches(
                    render_pass,
                    tuple(dynamic_draw_rects),
                    stream_kind="dynamic",
                )
                self._execute_rect_batch_ms_frame += (time.perf_counter() - rect_batch_started) * 1000.0
            if static_text_quads:
                text_batch_started = time.perf_counter()
                self._draw_text_batches(
                    render_pass,
                    tuple(static_text_quads),
                    stream_kind="static",
                    static_batch_key=tuple(static_text_packet_keys),
                )
                self._execute_text_batch_ms_frame += (time.perf_counter() - text_batch_started) * 1000.0
            if dynamic_text_quads:
                text_batch_started = time.perf_counter()
                self._draw_text_batches(
                    render_pass,
                    tuple(dynamic_text_quads),
                    stream_kind="dynamic",
                )
                self._execute_text_batch_ms_frame += (time.perf_counter() - text_batch_started) * 1000.0
        finally:
            self._execute_render_pass_record_ms_frame += (
                time.perf_counter() - render_record_started
            ) * 1000.0
            end = getattr(render_pass, "end", None)
            if callable(end):
                end_started = time.perf_counter()
                end()
                self._execute_render_pass_end_ms_frame += (
                    time.perf_counter() - end_started
                ) * 1000.0
        self._execute_draw_packets_total_ms_frame += (time.perf_counter() - draw_packets_started) * 1000.0

    def present(self) -> None:
        encoder = self._command_encoder
        if encoder is None:
            return
        if self._is_recovery_backoff_active():
            return
        finish = getattr(encoder, "finish", None)
        if not callable(finish):
            return
        self._present_attempts_last = 0
        retry_limit = self._effective_retry_limit(streak=self._present_failure_streak)
        for attempt in range(1, retry_limit + 1):
            self._present_attempts_last = attempt
            try:
                command_buffer = finish()
                submit = getattr(self._queue, "submit", None)
                if callable(submit):
                    submit([command_buffer])
                self._present_failure_streak = 0
                return
            except Exception as exc:
                self._present_failures += 1
                self._present_failure_streak += 1
                self._last_present_error = f"{exc.__class__.__name__}: {exc}"
                self._record_recovery_failure(kind="present")
                recovered = self._recover_surface_context(reason="present_submit")
                if recovered:
                    self._present_recoveries += 1
                    continue
                if attempt >= retry_limit:
                    raise RuntimeError(
                        "wgpu_present_failed "
                        f"attempts={self._present_attempts_last} "
                        f"present_mode={self._present_mode} "
                        f"size=({self._target_width},{self._target_height}) "
                        f"error={self._last_present_error}"
                    ) from exc

    def end_frame(self) -> None:
        self._command_encoder = None
        self._frame_color_view = None
        self._frame_in_flight = False
        return

    def close(self) -> None:
        self._queued_packets.clear()
        self._static_packet_rect_cache.clear()
        self._static_packet_text_quad_cache.clear()
        self._static_pass_expand_cache.clear()
        self._glyph_atlas_cache.clear()
        self._glyph_index_atlas_cache.clear()
        self._glyph_run_cache.clear()
        self._hb_font_cache.clear()
        self._font_vertical_metrics_cache.clear()
        self._upload_stream_buffer = None
        self._upload_stream_buffer_capacity = 0
        self._draw_vertex_buffer_static = None
        self._draw_vertex_buffer_static_capacity = 0
        self._draw_vertex_buffer_dynamic = None
        self._draw_vertex_buffer_dynamic_capacity = 0
        self._draw_text_vertex_buffer_static = None
        self._draw_text_vertex_buffer_static_capacity = 0
        self._draw_text_vertex_buffer_dynamic = None
        self._draw_text_vertex_buffer_dynamic_capacity = 0
        self._static_draw_cache_key = None
        self._static_draw_runs = ()
        self._static_render_bundle = None
        self._static_render_bundle_key = None
        self._static_text_cache_key = None
        self._static_text_vertex_count = 0
        self._static_text_bundle = None
        self._static_text_bundle_key = None
        self._text_bind_group = None
        self._text_sampler = None
        self._text_atlas_texture = None
        self._text_atlas_view = None
        self._text_atlas_pixels = bytearray()
        self._text_face = None
        self._font_blob = None
        self._frame_texture = None
        self._frame_texture_view = None
        self._frame_color_view = None
        self._command_encoder = None
        return

    def set_title(self, title: str) -> None:
        self._title = str(title)

    def reconfigure(self, event: WindowResizeEvent) -> None:
        self._window_width = max(1, int(event.physical_width))
        self._window_height = max(1, int(event.physical_height))
        self._target_width, self._target_height = self._resolve_internal_render_size(
            self._window_width,
            self._window_height,
        )
        self._surface_state["physical_width"] = self._window_width
        self._surface_state["physical_height"] = self._window_height
        self._surface_state["render_width"] = self._target_width
        self._surface_state["render_height"] = self._target_height
        self._surface_state["dpi_scale"] = float(event.dpi_scale)
        self._configure_canvas_context()
        self._rebuild_frame_targets_with_retry()
        self._static_packet_rect_cache.clear()
        self._static_packet_text_quad_cache.clear()
        self._static_pass_expand_cache.clear()
        self._static_draw_cache_key = None
        self._static_draw_runs = ()
        self._static_render_bundle = None
        self._static_render_bundle_key = None
        self._static_text_cache_key = None
        self._static_text_vertex_count = 0
        self._static_text_bundle = None
        self._static_text_bundle_key = None
        self._glyph_index_atlas_cache.clear()
        self._hb_font_cache.clear()
        self._font_vertical_metrics_cache.clear()
        return

    def resize_telemetry(self) -> dict[str, object]:
        raw_dpi = self._surface_state.get("dpi_scale", 1.0)
        if isinstance(raw_dpi, (int, float)):
            dpi = float(raw_dpi)
        else:
            dpi = 1.0
        return {
            "renderer_reused": True,
            "device_reused": True,
            "adapter_reused": True,
            "reconfigure_attempts": int(self._reconfigure_attempts_last),
            "reconfigure_failures": int(self._reconfigure_failures),
            "present_mode": str(self._present_mode),
            "present_mode_supported": tuple(self._present_mode_supported),
            "vsync_enabled": bool(self._vsync_enabled),
            "surface_format": str(self._surface_format),
            "width": int(self._target_width),
            "height": int(self._target_height),
            "window_width": int(self._window_width),
            "window_height": int(self._window_height),
            "render_width": int(self._target_width),
            "render_height": int(self._target_height),
            "render_scale": float(self._internal_render_scale),
            "dpi_scale": dpi,
            "acquire_attempts": int(self._acquire_attempts_last),
            "acquire_failures": int(self._acquire_failures),
            "acquire_recoveries": int(self._acquire_recoveries),
            "present_attempts": int(self._present_attempts_last),
            "present_failures": int(self._present_failures),
            "present_recoveries": int(self._present_recoveries),
            "last_present_error": str(self._last_present_error),
            "acquire_failure_streak": int(self._acquire_failure_streak),
            "present_failure_streak": int(self._present_failure_streak),
            "recovery_backoff_active": bool(self._is_recovery_backoff_active()),
            "recovery_backoff_events": int(self._recovery_backoff_events),
            "adaptive_present_mode_switches": int(self._adaptive_present_mode_switches),
            "effective_retry_limit": int(
                max(
                    self._effective_retry_limit(streak=self._acquire_failure_streak),
                    self._effective_retry_limit(streak=self._present_failure_streak),
                )
            ),
        }

    def _resolve_internal_render_size(self, width: int, height: int) -> tuple[int, int]:
        window_w = max(1, int(width))
        window_h = max(1, int(height))
        scale = max(0.1, float(self._internal_render_scale))
        if abs(scale - 1.0) < 1e-6:
            return (window_w, window_h)
        return (
            max(1, int(round(float(window_w) * scale))),
            max(1, int(round(float(window_h) * scale))),
        )

    def _request_adapter(self) -> tuple[object, str]:
        gpu = getattr(self._wgpu, "gpu", None)
        if gpu is None:
            raise WgpuInitError(
                "wgpu.gpu entrypoint unavailable",
                details={"selected_backend": "unknown", "adapter_info": {}},
            )
        backend_order = _resolve_backend_priority()
        request_adapter_sync = getattr(gpu, "request_adapter_sync", None)
        adapter = None
        selected_backend = "unknown"
        backend_errors: dict[str, str] = {}
        if callable(request_adapter_sync):
            for backend_name in backend_order:
                selected_backend = str(backend_name)
                try:
                    try:
                        adapter = request_adapter_sync(
                            power_preference="high-performance",
                            backend=backend_name,
                        )
                    except TypeError:
                        adapter = request_adapter_sync(power_preference="high-performance")
                except TypeError:
                    adapter = request_adapter_sync(power_preference="high-performance")
                except Exception as exc:
                    backend_errors[selected_backend] = f"{exc.__class__.__name__}: {exc}"
                    adapter = None
                    continue
                if adapter is not None:
                    break
        else:
            request_adapter = getattr(gpu, "request_adapter", None)
            if not callable(request_adapter):
                raise WgpuInitError(
                    "wgpu adapter request API unavailable",
                    details={
                        "selected_backend": "unknown",
                        "adapter_info": {},
                    },
                )
            for backend_name in backend_order:
                selected_backend = str(backend_name)
                try:
                    try:
                        adapter = request_adapter(
                            power_preference="high-performance",
                            backend=backend_name,
                        )
                    except TypeError:
                        adapter = request_adapter(power_preference="high-performance")
                except TypeError:
                    adapter = request_adapter(power_preference="high-performance")
                except Exception as exc:
                    backend_errors[selected_backend] = f"{exc.__class__.__name__}: {exc}"
                    adapter = None
                    continue
                if adapter is not None:
                    break
        if adapter is None:
            raise WgpuInitError(
                "wgpu adapter request returned None",
                details={
                    "selected_backend": selected_backend,
                    "attempted_backends": tuple(backend_order),
                    "backend_errors": dict(backend_errors),
                    "adapter_info": {},
                },
            )
        return adapter, selected_backend

    @staticmethod
    def _request_device(adapter: object) -> object:
        request_device_sync = getattr(adapter, "request_device_sync", None)
        if callable(request_device_sync):
            device = request_device_sync(label="engine.wgpu.device")
        else:
            request_device = getattr(adapter, "request_device", None)
            if not callable(request_device):
                raise RuntimeError("wgpu device request API unavailable")
            device = request_device(label="engine.wgpu.device")
        if device is None:
            raise WgpuInitError(
                "wgpu device request returned None",
                details={"selected_backend": "unknown", "adapter_info": {}},
            )
        return device

    @staticmethod
    def _extract_adapter_info(adapter: object) -> dict[str, object]:
        info = getattr(adapter, "info", None)
        if isinstance(info, dict):
            return {str(key): value for key, value in info.items()}
        return {}

    def _setup_surface_state(self) -> dict[str, object]:
        if "srgb" not in self._surface_format.lower():
            raise RuntimeError(
                "wgpu surface format must be sRGB for presentation "
                f"(configured={self._surface_format})"
            )
        state: dict[str, object] = {
            "surface_id": "",
            "backend": "unknown",
            "physical_width": self._window_width,
            "physical_height": self._window_height,
            "render_width": self._target_width,
            "render_height": self._target_height,
            "format": self._surface_format,
        }
        if self.surface is not None:
            state["surface_id"] = str(self.surface.surface_id)
            state["backend"] = str(self.surface.backend)
        state["present_mode"] = self._resolve_present_mode()
        self._present_mode = str(state["present_mode"])
        state["present_mode_supported"] = tuple(self._present_mode_supported)
        state["vsync_enabled"] = bool(self._vsync_enabled)
        return state

    def _setup_pipelines(self) -> None:
        create_shader_module = getattr(self._device, "create_shader_module", None)
        create_render_pipeline = getattr(self._device, "create_render_pipeline", None)
        if not callable(create_shader_module) or not callable(create_render_pipeline):
            self._geometry_pipeline = {"kind": "geometry", "format": self._surface_format}
            self._text_pipeline = {"kind": "text", "format": self._surface_format}
            self._setup_text_resources()
            return
        geometry_shader = create_shader_module(code=_GEOMETRY_WGSL)
        self._geometry_shader_module = geometry_shader
        text_shader = create_shader_module(code=_TEXT_WGSL)
        color_target = {
            "format": self._surface_format,
            "blend": {
                "color": {
                    "src_factor": "src-alpha",
                    "dst_factor": "one-minus-src-alpha",
                    "operation": "add",
                },
                "alpha": {
                    "src_factor": "one",
                    "dst_factor": "one-minus-src-alpha",
                    "operation": "add",
                },
            },
            "write_mask": 0xF,
        }
        geometry_descriptor = self._geometry_pipeline_descriptor(color_target, geometry_shader)
        text_descriptor = {
            "layout": "auto",
            "vertex": {
                "module": text_shader,
                "entry_point": "vs_main",
                "buffers": [
                    {
                        "array_stride": 32,
                        "step_mode": "vertex",
                        "attributes": [
                            {"shader_location": 0, "offset": 0, "format": "float32x2"},
                            {"shader_location": 1, "offset": 8, "format": "float32x2"},
                            {"shader_location": 2, "offset": 16, "format": "float32x4"},
                        ],
                    }
                ],
            },
            "fragment": {
                "module": text_shader,
                "entry_point": "fs_main",
                "targets": [
                    {
                        "format": self._surface_format,
                        "blend": {
                            "color": {
                                "src_factor": "src-alpha",
                                "dst_factor": "one-minus-src-alpha",
                                "operation": "add",
                            },
                            "alpha": {
                                "src_factor": "one",
                                "dst_factor": "one-minus-src-alpha",
                                "operation": "add",
                            },
                        },
                        "write_mask": 0xF,
                    }
                ],
            },
            "primitive": {"topology": "triangle-list"},
        }
        self._geometry_pipeline = create_render_pipeline(**geometry_descriptor)
        self._text_pipeline = create_render_pipeline(**text_descriptor)
        self._geometry_pipeline_cache[(0.1, 0.1, 0.1, 1.0)] = self._geometry_pipeline
        self._setup_text_resources()

    def _rebuild_frame_targets(self) -> None:
        create_texture = getattr(self._device, "create_texture", None)
        if not callable(create_texture):
            self._frame_texture = None
            self._frame_texture_view = None
            return
        usage = _resolve_texture_usage(self._wgpu)
        self._frame_texture = create_texture(
            size=(self._target_width, self._target_height, 1),
            format=self._surface_format,
            usage=usage,
            dimension="2d",
            mip_level_count=1,
            sample_count=1,
        )
        create_view = getattr(self._frame_texture, "create_view", None)
        self._frame_texture_view = create_view() if callable(create_view) else None

    def _rebuild_frame_targets_with_retry(self) -> None:
        self._reconfigure_attempts_last = 0
        for attempt in range(1, self._reconfigure_retry_limit + 1):
            self._reconfigure_attempts_last = attempt
            try:
                self._rebuild_frame_targets()
                return
            except Exception:
                self._reconfigure_failures += 1
                if attempt >= self._reconfigure_retry_limit:
                    raise RuntimeError(
                        "wgpu_surface_reconfigure_failed "
                        f"attempts={self._reconfigure_attempts_last} "
                        f"size=({self._target_width},{self._target_height}) "
                        f"format={self._surface_format} "
                        f"present_mode={self._present_mode}"
                    ) from None

    def _setup_text_resources(self) -> None:
        self._text_bind_group = None
        self._text_sampler = None
        self._text_atlas_texture = None
        self._text_atlas_view = None
        self._text_atlas_pixels = bytearray(
            int(self._text_atlas_width) * int(self._text_atlas_height)
        )
        self._text_atlas_cursor_x = 1
        self._text_atlas_cursor_y = 1
        self._text_atlas_row_height = 0
        self._text_atlas_dirty = False
        self._glyph_atlas_cache.clear()
        self._glyph_index_atlas_cache.clear()
        self._glyph_run_cache.clear()
        self._hb_font_cache.clear()
        self._font_vertical_metrics_cache.clear()
        self._static_packet_text_quad_cache.clear()
        self._static_pass_expand_cache.clear()
        self._text_face = _try_create_freetype_face(self._font_path)
        self._font_blob = _load_font_blob(self._font_path)

        create_texture = getattr(self._device, "create_texture", None)
        if not callable(create_texture):
            return
        texture_usage = _resolve_text_texture_usage(self._wgpu)
        try:
            texture = create_texture(
                size=(int(self._text_atlas_width), int(self._text_atlas_height), 1),
                dimension="2d",
                format="r8unorm",
                usage=texture_usage,
            )
        except Exception:
            return
        create_view = getattr(texture, "create_view", None)
        if not callable(create_view):
            return
        view = create_view()
        create_sampler = getattr(self._device, "create_sampler", None)
        if not callable(create_sampler):
            return
        try:
            sampler = create_sampler(
                mag_filter="linear",
                min_filter="linear",
                mipmap_filter="nearest",
                address_mode_u="clamp-to-edge",
                address_mode_v="clamp-to-edge",
            )
        except Exception:
            return
        if self._text_pipeline is None:
            return
        get_bind_group_layout = getattr(self._text_pipeline, "get_bind_group_layout", None)
        create_bind_group = getattr(self._device, "create_bind_group", None)
        if not callable(get_bind_group_layout) or not callable(create_bind_group):
            return
        try:
            layout = get_bind_group_layout(0)
            bind_group = create_bind_group(
                layout=layout,
                entries=[
                    {"binding": 0, "resource": view},
                    {"binding": 1, "resource": sampler},
                ],
            )
        except Exception:
            return
        self._text_atlas_texture = cast(object, texture)
        self._text_atlas_view = cast(object, view)
        self._text_sampler = cast(object, sampler)
        self._text_bind_group = cast(object, bind_group)

    def _supports_text_atlas(self) -> bool:
        return (
            self._text_pipeline is not None
            and self._text_bind_group is not None
            and self._text_atlas_texture is not None
        )

    def _upload_text_atlas_if_needed(self) -> None:
        if not self._text_atlas_dirty:
            return
        if self._text_atlas_texture is None:
            return
        write_texture = getattr(self._queue, "write_texture", None)
        if not callable(write_texture):
            return
        payload = bytes(self._text_atlas_pixels)
        upload_started = time.perf_counter()
        try:
            write_texture(
                {"texture": self._text_atlas_texture, "origin": (0, 0, 0)},
                payload,
                {
                    "offset": 0,
                    "bytes_per_row": int(self._text_atlas_width),
                    "rows_per_image": int(self._text_atlas_height),
                },
                (int(self._text_atlas_width), int(self._text_atlas_height), 1),
            )
        except Exception:
            return
        self._execute_atlas_upload_ms_frame += (time.perf_counter() - upload_started) * 1000.0
        self._execute_atlas_upload_bytes_frame += int(len(payload))
        self._execute_atlas_upload_count_frame += 1
        self._text_atlas_dirty = False

    def _resolve_present_mode(self) -> str:
        runtime_config = get_runtime_config()
        supported = tuple(item.strip().lower() for item in runtime_config.renderer.present_modes if item.strip())
        if not supported:
            supported = ("fifo", "mailbox", "immediate")
        self._present_mode_supported = tuple(supported)
        vsync = bool(runtime_config.render.vsync)
        self._vsync_enabled = bool(vsync)
        if vsync:
            preferred = ("fifo", "mailbox", "immediate")
        else:
            preferred = ("mailbox", "immediate", "fifo")
        for mode in preferred:
            if mode in supported:
                return mode
        return "fifo"

    def _stage_draw_packets(self, packets: tuple[_DrawPacket, ...]) -> None:
        stage_started = time.perf_counter()
        packet_count = int(len(packets))
        if packet_count <= 0:
            self._upload_mode_last = "none"
            self._uploaded_packet_count = 0
            self._execute_stage_upload_ms_frame += (time.perf_counter() - stage_started) * 1000.0
            return
        if packet_count <= self._upload_threshold_packets:
            self._upload_mode_last = "full_rewrite"
            self._uploaded_packet_count = packet_count
            self._upload_full_rewrite(packet_count)
            self._execute_stage_upload_ms_frame += (time.perf_counter() - stage_started) * 1000.0
            return
        self._upload_mode_last = "ring_buffer"
        self._uploaded_packet_count = packet_count
        self._upload_ring_buffer(packet_count)
        self._execute_stage_upload_ms_frame += (time.perf_counter() - stage_started) * 1000.0

    def _upload_full_rewrite(self, packet_count: int) -> None:
        size = max(256, int(packet_count * 64))
        self._ensure_upload_stream_capacity(size)

    def _upload_ring_buffer(self, packet_count: int) -> None:
        size = max(1024, int(packet_count * 64))
        self._ensure_upload_stream_capacity(size)
        self._stream_write_cursor = (self._stream_write_cursor + packet_count) % 1_000_000

    def _ensure_upload_stream_capacity(self, minimum_bytes: int) -> object | None:
        required = max(256, int(minimum_bytes))
        if (
            self._upload_stream_buffer is not None
            and self._upload_stream_buffer_capacity >= required
        ):
            return self._upload_stream_buffer
        create_buffer = getattr(self._device, "create_buffer", None)
        if not callable(create_buffer):
            return None
        usage = _resolve_buffer_usage(self._wgpu)
        capacity = 4096
        while capacity < required:
            capacity *= 2
        try:
            buffer = create_buffer(size=capacity, usage=usage, mapped_at_creation=False)
        except Exception:
            return None
        self._upload_stream_buffer = cast(object, buffer)
        self._upload_stream_buffer_capacity = int(capacity)
        return cast(object, buffer)

    def _init_canvas_surface_context(self) -> None:
        provider = self.surface.provider if self.surface is not None else None
        self._canvas = provider
        get_context = getattr(provider, "get_context", None)
        if not callable(get_context):
            return
        context = get_context("wgpu")
        if context is None:
            return
        self._canvas_context = context
        self._configure_canvas_context()

    def _acquire_frame_color_view(self) -> object | None:
        context = self._canvas_context
        if context is None:
            return None
        if self._is_recovery_backoff_active():
            return None
        get_current_texture = getattr(context, "get_current_texture", None)
        if not callable(get_current_texture):
            return None
        self._acquire_attempts_last = 0
        retry_limit = self._effective_retry_limit(streak=self._acquire_failure_streak)
        for attempt in range(1, retry_limit + 1):
            self._acquire_attempts_last = attempt
            try:
                texture = get_current_texture()
                create_view = getattr(texture, "create_view", None)
                self._acquire_failure_streak = 0
                if callable(create_view):
                    return cast(object, create_view())
                return cast(object, texture)
            except Exception:
                self._acquire_failures += 1
                self._acquire_failure_streak += 1
                self._record_recovery_failure(kind="acquire")
                if self._recover_surface_context(reason="acquire_current_texture"):
                    self._acquire_recoveries += 1
                    continue
                return None
        return None

    def _configure_canvas_context(self) -> bool:
        context = self._canvas_context
        if context is None:
            return False
        configure = getattr(context, "configure", None)
        if not callable(configure):
            return False
        try:
            configure(
                device=self._device,
                format=self._surface_format,
                usage=_resolve_texture_usage(self._wgpu),
                present_mode=self._present_mode,
                alpha_mode="premultiplied",
                size=(int(self._target_width), int(self._target_height)),
            )
            return True
        except TypeError:
            try:
                configure(
                    device=self._device,
                    format=self._surface_format,
                    present_mode=self._present_mode,
                    size=(int(self._target_width), int(self._target_height)),
                )
                return True
            except TypeError:
                try:
                    configure(device=self._device, format=self._surface_format)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def _recover_surface_context(self, *, reason: str) -> bool:
        _ = reason
        configured = self._configure_canvas_context()
        try:
            self._rebuild_frame_targets_with_retry()
            rebuilt = True
        except Exception:
            rebuilt = False
        if configured or rebuilt:
            self._maybe_apply_adaptive_present_mode()
        return bool(configured or rebuilt)

    def _effective_retry_limit(self, *, streak: int) -> int:
        extra = max(0, int(streak)) // max(1, int(self._recovery_failure_streak_threshold))
        return min(
            int(self._reconfigure_retry_limit_max),
            int(self._reconfigure_retry_limit) + extra,
        )

    def _record_recovery_failure(self, *, kind: str) -> None:
        _ = kind
        streak = max(int(self._acquire_failure_streak), int(self._present_failure_streak))
        if streak < int(self._recovery_failure_streak_threshold):
            return
        now = time.perf_counter()
        self._recovery_backoff_until_s = max(
            float(self._recovery_backoff_until_s),
            now + float(self._recovery_cooldown_s),
        )
        self._recovery_backoff_events += 1

    def _is_recovery_backoff_active(self) -> bool:
        return time.perf_counter() < float(self._recovery_backoff_until_s)

    def _maybe_apply_adaptive_present_mode(self) -> None:
        if self._present_mode == "fifo":
            return
        if "fifo" not in self._present_mode_supported:
            return
        if max(self._acquire_failure_streak, self._present_failure_streak) < int(
            self._recovery_failure_streak_threshold
        ):
            return
        self._present_mode = "fifo"
        if self._configure_canvas_context():
            self._adaptive_present_mode_switches += 1

    def _geometry_pipeline_descriptor(self, color_target: object, shader: object) -> dict[str, object]:
        return {
            "layout": "auto",
            "vertex": {
                "module": shader,
                "entry_point": "vs_main",
                "buffers": [
                    {
                        "array_stride": 24,
                        "step_mode": "vertex",
                        "attributes": [
                            {"shader_location": 0, "offset": 0, "format": "float32x2"},
                            {"shader_location": 1, "offset": 8, "format": "float32x4"},
                        ],
                    }
                ],
            },
            "fragment": {
                "module": shader,
                "entry_point": "fs_main",
                "targets": [color_target],
            },
            "primitive": {"topology": "triangle-list"},
        }

    def _pipeline_for_color(self, color: tuple[float, float, float, float]) -> object | None:
        _ = color
        return self._geometry_pipeline

    def _packet_draw_rects(
        self,
        packet: _DrawPacket,
        *,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
    ) -> tuple["_DrawRect", ...]:
        raw_data = getattr(packet, "data", ())
        layer = int(getattr(packet, "layer", 0))
        payload: dict[str, object] = {}
        if isinstance(raw_data, tuple):
            for item in raw_data:
                if isinstance(item, tuple) and len(item) == 2:
                    payload[str(item[0])] = item[1]
        linear = payload.get("linear_rgba", (1.0, 1.0, 1.0, 1.0))
        color = _normalize_rgba(linear)
        kind = str(getattr(packet, "kind", ""))
        if not kind:
            return ()
        if kind == "fill_window":
            return (
                _DrawRect(
                    layer=layer,
                    x=0.0,
                    y=0.0,
                    w=float(self._target_width),
                    h=float(self._target_height),
                    color=color,
                ),
            )
        if kind == "rect":
            if payload:
                mapped = self._map_design_rect(
                    _rect_from_payload(payload, color=color), sx=sx, sy=sy, ox=ox, oy=oy
                )
                return (self._with_layer(mapped, layer),)
            return (
                _DrawRect(
                    layer=layer,
                    x=0.0,
                    y=0.0,
                    w=float(self._target_width),
                    h=float(self._target_height),
                    color=color,
                ),
            )
        if kind == "rounded_rect":
            if not payload:
                return ()
            mapped = self._map_design_rect(
                _rect_from_payload(payload, color=color), sx=sx, sy=sy, ox=ox, oy=oy
            )
            radius_design = _payload_float(payload, "radius", 0.0)
            radius_px = max(0.0, float(radius_design) * max(abs(float(sx)), abs(float(sy))))
            if 0.0 < radius_px < 2.5:
                return (self._with_layer(mapped, layer),)
            return tuple(
                self._with_layer(rect, layer)
                for rect in _rounded_rect_draw_rects(
                    layer=layer,
                    x=mapped.x,
                    y=mapped.y,
                    w=mapped.w,
                    h=mapped.h,
                    radius=radius_px,
                    color=color,
                )
            )
        if kind == "gradient_rect":
            if not payload:
                return ()
            top_color = _normalize_rgba(payload.get("linear_rgba", (1.0, 1.0, 1.0, 1.0)))
            bottom_color = _normalize_rgba(payload.get("linear_secondary_rgba", top_color))
            mapped = self._map_design_rect(
                _rect_from_payload(payload, color=top_color), sx=sx, sy=sy, ox=ox, oy=oy
            )
            steps = max(2, min(6, int(round(_payload_float(payload, "thickness", 3.0)))))
            step_h = max(1.0, mapped.h / float(steps))
            gradient_rects: list[_DrawRect] = []
            for i in range(steps):
                t = float(i) / float(max(1, steps - 1))
                c = (
                    _lerp(top_color[0], bottom_color[0], t),
                    _lerp(top_color[1], bottom_color[1], t),
                    _lerp(top_color[2], bottom_color[2], t),
                    _lerp(top_color[3], bottom_color[3], t),
                )
                gradient_rects.append(
                    self._with_layer(
                        _DrawRect(
                            layer=layer,
                            x=mapped.x,
                            y=mapped.y + (float(i) * step_h),
                            w=mapped.w,
                            h=max(1.0, step_h + 0.5),
                            color=c,
                        ),
                        layer,
                    )
                )
            return tuple(gradient_rects)
        if kind == "stroke_rect":
            if not payload:
                return ()
            mapped = self._map_design_rect(
                _rect_from_payload(payload, color=color), sx=sx, sy=sy, ox=ox, oy=oy
            )
            thickness_design = _payload_float(payload, "thickness", 1.0)
            thickness_h = _stroke_px(thickness_design, sy)
            thickness_v = _stroke_px(thickness_design, sx)
            x0 = _snap_to_pixel(mapped.x)
            y0 = _snap_to_pixel(mapped.y)
            w0 = max(1.0, _snap_to_pixel(mapped.w))
            h0 = max(1.0, _snap_to_pixel(mapped.h))
            return (
                self._with_layer(
                    _DrawRect(
                        layer=layer,
                        x=x0,
                        y=y0,
                        w=w0,
                        h=thickness_h,
                        color=color,
                    ),
                    layer,
                ),
                self._with_layer(
                    _DrawRect(
                        layer=layer,
                        x=x0,
                        y=y0 + h0 - thickness_h,
                        w=w0,
                        h=thickness_h,
                        color=color,
                    ),
                    layer,
                ),
                self._with_layer(
                    _DrawRect(
                        layer=layer,
                        x=x0,
                        y=y0,
                        w=thickness_v,
                        h=h0,
                        color=color,
                    ),
                    layer,
                ),
                self._with_layer(
                    _DrawRect(
                        layer=layer,
                        x=x0 + w0 - thickness_v,
                        y=y0,
                        w=thickness_v,
                        h=h0,
                        color=color,
                    ),
                    layer,
                ),
            )
        if kind == "shadow_rect":
            if not payload:
                return ()
            mapped = self._map_design_rect(
                _rect_from_payload(payload, color=color), sx=sx, sy=sy, ox=ox, oy=oy
            )
            spread_design = max(1.0, _payload_float(payload, "thickness", 2.0))
            spread = max(1.0, spread_design * max(abs(float(sx)), abs(float(sy))))
            layers = max(1, min(2, int(round(_payload_float(payload, "shadow_layers", 2.0)))))
            corner_radius_design = max(0.0, _payload_float(payload, "radius", 0.0))
            corner_radius_px = corner_radius_design * max(abs(float(sx)), abs(float(sy)))
            x0 = _snap_to_pixel(mapped.x)
            y0 = _snap_to_pixel(mapped.y)
            w0 = max(1.0, _snap_to_pixel(mapped.w))
            h0 = max(1.0, _snap_to_pixel(mapped.h))
            shadow_rects: list[_DrawRect] = []
            for idx in range(layers, 0, -1):
                t = float(idx) / float(layers)
                pad = spread * t
                drop_y = pad * 0.6
                rgba = (
                    color[0],
                    color[1],
                    color[2],
                    color[3] * (0.50 * (0.60 + (0.40 * t))),
                )
                rounded = _rounded_rect_draw_rects(
                    layer=layer,
                    x=float(x0 - pad),
                    y=float(y0 - pad + drop_y),
                    w=float(w0 + (2.0 * pad)),
                    h=float(h0 + (2.0 * pad)),
                    radius=max(0.0, corner_radius_px + (pad * 0.9)),
                    color=rgba,
                    max_steps=8,
                )
                shadow_rects.extend(
                    self._with_layer(rect, layer)
                    for rect in rounded
                )
            return tuple(shadow_rects)
        if kind == "grid":
            return tuple(
                self._with_layer(
                    self._map_design_rect(rect, sx=sx, sy=sy, ox=ox, oy=oy), layer
                )
                for rect in _grid_draw_rects(payload, color=color)
            )
        if kind == "text":
            return tuple(
                self._with_layer(
                    self._map_design_rect(rect, sx=sx, sy=sy, ox=ox, oy=oy), layer
                )
                for rect in _text_draw_rects(payload, color=color)
            )
        return ()

    def _packet_draw_rects_cached(
        self,
        packet: _DrawPacket,
        *,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
        static_cache_key: tuple[object, ...] | None = None,
        viewport_cache_key: tuple[object, ...] | None = None,
    ) -> tuple["_DrawRect", ...]:
        if not _packet_is_static(packet):
            return self._packet_draw_rects(packet, sx=sx, sy=sy, ox=ox, oy=oy)
        cache_key = static_cache_key
        if cache_key is None:
            cache_key = self._build_static_packet_cache_key(
                packet,
                sx=sx,
                sy=sy,
                ox=ox,
                oy=oy,
                viewport_cache_key=viewport_cache_key,
            )
        cached = self._static_packet_rect_cache.get(cache_key)
        if cached is not None:
            return cached
        rects = self._packet_draw_rects(packet, sx=sx, sy=sy, ox=ox, oy=oy)
        self._static_packet_rect_cache[cache_key] = rects
        return rects

    def _build_static_packet_cache_key(
        self,
        packet: _DrawPacket,
        *,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
        viewport_cache_key: tuple[object, ...] | None = None,
    ) -> tuple[object, ...]:
        cache_base = getattr(packet, "engine_cache_base", None)
        if cache_base is None:
            version_token = _packet_version_token(packet)
            if version_token is None:
                version_token = (
                    int(id(packet.data)),
                    int(id(packet.transform)),
                )
            version_key = _version_fingerprint(version_token)
            cache_base = (
                str(packet.kind),
                int(packet.layer),
                str(packet.sort_key),
                version_key,
            )
        if viewport_cache_key is None:
            viewport_cache_key = (
                float(sx),
                float(sy),
                float(ox),
                float(oy),
                int(self._target_width),
                int(self._target_height),
                int(self._design_width),
                int(self._design_height),
                bool(self._preserve_aspect),
            )
        return cache_base + tuple(viewport_cache_key)

    def _packet_text_quads(
        self,
        packet: _DrawPacket,
        *,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
        static_cache_key: tuple[object, ...] | None = None,
        viewport_cache_key: tuple[object, ...] | None = None,
    ) -> tuple[_DrawTextQuad, ...]:
        if not self._supports_text_atlas():
            return ()
        is_static_packet = _packet_is_static(packet)
        cache_key: tuple[object, ...] | None = None
        if is_static_packet:
            cache_key = static_cache_key
            if cache_key is None:
                cache_key = self._build_static_packet_cache_key(
                    packet,
                    sx=sx,
                    sy=sy,
                    ox=ox,
                    oy=oy,
                    viewport_cache_key=viewport_cache_key,
                )
            cached = self._static_packet_text_quad_cache.get(cache_key)
            if cached is not None:
                return cached
        raw_data = getattr(packet, "data", ())
        if not isinstance(raw_data, tuple):
            return ()
        text_raw: object = ""
        font_size_raw: object = 18.0
        x_raw: object = 0.0
        y_raw: object = 0.0
        anchor_raw: object = "top-left"
        color_raw: object = (1.0, 1.0, 1.0, 1.0)
        for item in raw_data:
            if not (isinstance(item, tuple) and len(item) == 2):
                continue
            key, value = item
            key_name = str(key)
            if key_name == "text":
                text_raw = value
            elif key_name == "font_size":
                font_size_raw = value
            elif key_name == "x":
                x_raw = value
            elif key_name == "y":
                y_raw = value
            elif key_name == "anchor":
                anchor_raw = value
            elif key_name == "linear_rgba":
                color_raw = value
        if not isinstance(text_raw, str):
            return ()
        text = text_raw.strip("\n")
        if not text:
            return ()
        font_size_px = 18
        if isinstance(font_size_raw, (int, float)):
            font_size_px = max(6, int(round(float(font_size_raw))))
        viewport_scale = max(
            1.0,
            abs(float(sx)),
            abs(float(sy)),
        )
        run = self._layout_glyph_run(
            text=text,
            font_size_px=font_size_px,
            raster_scale=viewport_scale,
        )
        if run is None or not run.placements:
            return ()
        x = float(x_raw) if isinstance(x_raw, (int, float)) else 0.0
        y = float(y_raw) if isinstance(y_raw, (int, float)) else 0.0
        anchor = str(anchor_raw).strip().lower() if isinstance(anchor_raw, str) else "top-left"
        origin_x, origin_y = _anchor_to_origin(anchor, x, y, run.width, run.height)
        color = _normalize_rgba(color_raw)
        layer = int(getattr(packet, "layer", 0))
        out: list[_DrawTextQuad] = []
        for placement in run.placements:
            mx = (float(origin_x) + placement.x) * sx + ox
            my = (float(origin_y) + placement.y) * sy + oy
            mw = max(1.0, placement.width * sx)
            mh = max(1.0, placement.height * sy)
            # Snap quads to pixel grid to avoid fractional UV sampling blur.
            mx = float(round(mx))
            my = float(round(my))
            mw = float(max(1.0, round(mw)))
            mh = float(max(1.0, round(mh)))
            out.append(
                _DrawTextQuad(
                    layer=layer,
                    x=mx,
                    y=my,
                    w=mw,
                    h=mh,
                    u0=float(placement.u0),
                    v0=float(placement.v0),
                    u1=float(placement.u1),
                    v1=float(placement.v1),
                    color=color,
                )
            )
        quads = tuple(out)
        if is_static_packet and cache_key is not None:
            self._static_packet_text_quad_cache[cache_key] = quads
        return quads

    def _layout_glyph_run(
        self,
        *,
        text: str,
        font_size_px: int,
        raster_scale: float = 1.0,
    ) -> _GlyphRunLayout | None:
        layout_started = time.perf_counter()
        try:
            if self._text_face is None:
                return None
            design_size_px = int(max(1, font_size_px))
            scale = max(1.0, float(raster_scale))
            raster_size_px = max(1, int(round(float(design_size_px) * scale)))
            run_key = (self._font_path, design_size_px, raster_size_px, str(text))
            cached = self._glyph_run_cache.get(run_key)
            if cached is not None:
                return cached
            shaped = self._shape_text_run(text=text, font_size_px=raster_size_px)
            if not shaped:
                raise RuntimeError("native text shaping returned no glyphs for non-empty text")
            layout = self._layout_shaped_glyph_run(
                shaped=shaped,
                font_size_px=raster_size_px,
                output_size_px=design_size_px,
            )
            if layout is None:
                raise RuntimeError("native shaped glyph layout produced no drawable placements")
            self._glyph_run_cache[run_key] = layout
            return layout
        finally:
            self._execute_text_layout_ms_frame += (time.perf_counter() - layout_started) * 1000.0

    def _shape_text_run(self, *, text: str, font_size_px: int) -> tuple[_ShapedGlyph, ...]:
        shape_started = time.perf_counter()
        self._execute_text_shape_calls_frame += 1
        try:
            if _HB is None:
                return ()
            if not text:
                return ()
            hb_font = self._hb_font_for_size(font_size_px=font_size_px)
            if hb_font is None:
                return ()
            buffer = _HB.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            _HB.shape(hb_font, buffer, {"kern": True, "liga": True, "clig": True})
            infos = list(getattr(buffer, "glyph_infos", ()) or ())
            positions = list(getattr(buffer, "glyph_positions", ()) or ())
            if not infos or len(infos) != len(positions):
                return ()
            out: list[_ShapedGlyph] = []
            scale = 1.0 / 64.0
            for info, pos in zip(infos, positions, strict=False):
                out.append(
                    _ShapedGlyph(
                        glyph_index=int(getattr(info, "codepoint", 0)),
                        x_offset=float(getattr(pos, "x_offset", 0)) * scale,
                        y_offset=float(getattr(pos, "y_offset", 0)) * scale,
                        x_advance=float(getattr(pos, "x_advance", 0)) * scale,
                        y_advance=float(getattr(pos, "y_advance", 0)) * scale,
                    )
                )
            return tuple(out)
        finally:
            self._execute_text_shape_ms_frame += (time.perf_counter() - shape_started) * 1000.0

    def _hb_font_for_size(self, *, font_size_px: int) -> object | None:
        if _HB is None:
            return None
        key = int(max(1, font_size_px))
        cached = self._hb_font_cache.get(key)
        if cached is not None:
            return cached
        blob = self._font_blob
        if not blob:
            return None
        try:
            face = _HB.Face(blob)
            font = _HB.Font(face)
            _HB.ot_font_set_funcs(font)
            scale = int(max(1, key) * 64)
            font.scale = (scale, scale)
            self._hb_font_cache[key] = cast(object, font)
            return cast(object, font)
        except Exception:
            return None

    def _layout_shaped_glyph_run(
        self,
        *,
        shaped: tuple[_ShapedGlyph, ...],
        font_size_px: int,
        output_size_px: int,
    ) -> _GlyphRunLayout | None:
        source_size_px = int(max(1, font_size_px))
        output_size = float(max(1, output_size_px))
        source_size = float(source_size_px)
        scale_to_output = output_size / source_size
        metrics = self._font_vertical_metrics_for_size(font_size_px=source_size_px)
        pen_x = 0.0
        pen_y = 0.0
        placements_raw: list[tuple[float, float, float, float, float, float, float, float]] = []
        min_x = 0.0
        min_y = 0.0
        max_x = 0.0
        max_y = 0.0
        for glyph in shaped:
            entry = self._glyph_atlas_entry_by_index(
                glyph_index=glyph.glyph_index,
                font_size_px=source_size_px,
            )
            if entry is None:
                pen_x += max(1.0, float(glyph.x_advance))
                pen_y += float(glyph.y_advance)
                continue
            gx = pen_x + float(glyph.x_offset) + float(entry.bearing_x)
            gy = pen_y - float(glyph.y_offset) - float(entry.bearing_y)
            gw = max(0.0, float(entry.width))
            gh = max(0.0, float(entry.height))
            if gw > 0.0 and gh > 0.0:
                placements_raw.append((gx, gy, gw, gh, entry.u0, entry.v0, entry.u1, entry.v1))
                min_x = min(min_x, gx)
                min_y = min(min_y, gy)
                max_x = max(max_x, gx + gw)
                max_y = max(max_y, gy + gh)
            pen_x += max(1.0, float(glyph.x_advance))
            pen_y += float(glyph.y_advance)
        if not placements_raw:
            return None
        nominal_ascent = float(metrics.ascent)
        nominal_descent = max(float(metrics.descent), float(metrics.line_height) - nominal_ascent)
        line_top = min(-nominal_ascent, min_y)
        line_bottom = max(nominal_descent, max_y)
        width = max(1.0, max_x - min_x)
        height = max(1.0, line_bottom - line_top)
        baseline = max(0.0, -line_top)
        placements = tuple(
            _GlyphPlacement(
                x=(gx - min_x) * scale_to_output,
                y=(gy - line_top) * scale_to_output,
                width=gw * scale_to_output,
                height=gh * scale_to_output,
                u0=u0,
                v0=v0,
                u1=u1,
                v1=v1,
            )
            for gx, gy, gw, gh, u0, v0, u1, v1 in placements_raw
        )
        return _GlyphRunLayout(
            width=width * scale_to_output,
            height=height * scale_to_output,
            baseline=baseline * scale_to_output,
            placements=placements,
        )

    def _font_vertical_metrics_for_size(self, *, font_size_px: int) -> _FontVerticalMetrics:
        size_px = int(max(1, font_size_px))
        cached = self._font_vertical_metrics_cache.get(size_px)
        if cached is not None:
            return cached
        face = self._text_face
        if face is None:
            metrics = _FontVerticalMetrics(
                ascent=float(size_px) * 0.8,
                descent=float(size_px) * 0.2,
                line_height=float(size_px),
            )
            self._font_vertical_metrics_cache[size_px] = metrics
            return metrics
        try:
            set_pixel_sizes = getattr(face, "set_pixel_sizes", None)
            if callable(set_pixel_sizes):
                set_pixel_sizes(0, size_px)
            size_obj = getattr(face, "size", None)
            raw_metrics = getattr(size_obj, "metrics", None)
            asc_raw = getattr(raw_metrics, "ascender", 0)
            desc_raw = getattr(raw_metrics, "descender", 0)
            height_raw = getattr(raw_metrics, "height", 0)
            asc = float(asc_raw) / 64.0 if isinstance(asc_raw, (int, float)) else 0.0
            desc = -float(desc_raw) / 64.0 if isinstance(desc_raw, (int, float)) else 0.0
            line_h = float(height_raw) / 64.0 if isinstance(height_raw, (int, float)) else 0.0
            ascent = max(0.0, asc)
            descent = max(0.0, desc)
            line_height = max(ascent + descent, line_h)
            if line_height <= 0.0:
                line_height = float(size_px)
            if ascent <= 0.0 and descent <= 0.0:
                ascent = line_height * 0.8
                descent = max(1.0, line_height - ascent)
            metrics = _FontVerticalMetrics(
                ascent=ascent,
                descent=descent,
                line_height=line_height,
            )
        except Exception:
            line_height = float(size_px)
            metrics = _FontVerticalMetrics(
                ascent=line_height * 0.8,
                descent=max(1.0, line_height * 0.2),
                line_height=line_height,
            )
        self._font_vertical_metrics_cache[size_px] = metrics
        return metrics

    def _glyph_atlas_entry(self, *, ch: str, font_size_px: int) -> _GlyphAtlasEntry | None:
        atlas_pad = 1
        key = (int(font_size_px), str(ch))
        cached = self._glyph_atlas_cache.get(key)
        if cached is not None:
            return cached
        raster = _rasterize_glyph_bitmap(
            face=self._text_face,
            character=ch,
            size_px=font_size_px,
        )
        if raster is None:
            return None
        width, rows, left, top, advance, alpha_bytes = raster
        if width <= 0 or rows <= 0:
            entry = _GlyphAtlasEntry(
                u0=0.0,
                v0=0.0,
                u1=0.0,
                v1=0.0,
                width=0.0,
                height=0.0,
                bearing_x=float(left),
                bearing_y=float(top),
                advance=float(max(1.0, advance)),
            )
            self._glyph_atlas_cache[key] = entry
            return entry
        atlas_xy = self._pack_atlas_region(
            width=width + (atlas_pad * 2),
            height=rows + (atlas_pad * 2),
        )
        if atlas_xy is None:
            return None
        dst_x, dst_y = atlas_xy
        inner_x = dst_x + atlas_pad
        inner_y = dst_y + atlas_pad
        self._blit_alpha_to_atlas(
            x=inner_x,
            y=inner_y,
            width=width,
            height=rows,
            data=alpha_bytes,
            pad=atlas_pad,
        )
        atlas_w = max(1, int(self._text_atlas_width))
        atlas_h = max(1, int(self._text_atlas_height))
        u0, u1 = _safe_uv_bounds(start_px=inner_x, size_px=width, atlas_size_px=atlas_w)
        v0, v1 = _safe_uv_bounds(start_px=inner_y, size_px=rows, atlas_size_px=atlas_h)
        entry = _GlyphAtlasEntry(
            u0=u0,
            v0=v0,
            u1=u1,
            v1=v1,
            width=float(max(1, width)),
            height=float(max(1, rows)),
            bearing_x=float(left),
            bearing_y=float(top),
            advance=float(max(1, advance)),
        )
        self._glyph_atlas_cache[key] = entry
        return entry

    def _glyph_atlas_entry_by_index(
        self, *, glyph_index: int, font_size_px: int
    ) -> _GlyphAtlasEntry | None:
        atlas_pad = 1
        size_px = int(max(1, font_size_px))
        key = (size_px, int(max(0, glyph_index)))
        cached = self._glyph_index_atlas_cache.get(key)
        if cached is not None:
            return cached
        raster = _rasterize_glyph_index_bitmap(
            face=self._text_face,
            glyph_index=int(max(0, glyph_index)),
            size_px=size_px,
        )
        if raster is None:
            return None
        width, rows, left, top, advance, alpha_bytes = raster
        if width <= 0 or rows <= 0:
            entry = _GlyphAtlasEntry(
                u0=0.0,
                v0=0.0,
                u1=0.0,
                v1=0.0,
                width=0.0,
                height=0.0,
                bearing_x=float(left),
                bearing_y=float(top),
                advance=float(max(1.0, advance)),
            )
            self._glyph_index_atlas_cache[key] = entry
            return entry
        atlas_xy = self._pack_atlas_region(
            width=width + (atlas_pad * 2),
            height=rows + (atlas_pad * 2),
        )
        if atlas_xy is None:
            return None
        dst_x, dst_y = atlas_xy
        inner_x = dst_x + atlas_pad
        inner_y = dst_y + atlas_pad
        self._blit_alpha_to_atlas(
            x=inner_x,
            y=inner_y,
            width=width,
            height=rows,
            data=alpha_bytes,
            pad=atlas_pad,
        )
        atlas_w = max(1, int(self._text_atlas_width))
        atlas_h = max(1, int(self._text_atlas_height))
        u0, u1 = _safe_uv_bounds(start_px=inner_x, size_px=width, atlas_size_px=atlas_w)
        v0, v1 = _safe_uv_bounds(start_px=inner_y, size_px=rows, atlas_size_px=atlas_h)
        entry = _GlyphAtlasEntry(
            u0=u0,
            v0=v0,
            u1=u1,
            v1=v1,
            width=float(max(1, width)),
            height=float(max(1, rows)),
            bearing_x=float(left),
            bearing_y=float(top),
            advance=float(max(1, advance)),
        )
        self._glyph_index_atlas_cache[key] = entry
        return entry

    def _pack_atlas_region(self, *, width: int, height: int) -> tuple[int, int] | None:
        region_w = max(1, int(width))
        region_h = max(1, int(height))
        atlas_w = max(2, int(self._text_atlas_width))
        atlas_h = max(2, int(self._text_atlas_height))
        if region_w + 2 >= atlas_w or region_h + 2 >= atlas_h:
            return None
        cursor_x = int(self._text_atlas_cursor_x)
        cursor_y = int(self._text_atlas_cursor_y)
        row_h = int(self._text_atlas_row_height)
        if cursor_x + region_w + 1 >= atlas_w:
            cursor_x = 1
            cursor_y += row_h + 1
            row_h = 0
        if cursor_y + region_h + 1 >= atlas_h:
            return None
        self._text_atlas_cursor_x = cursor_x + region_w + 1
        self._text_atlas_cursor_y = cursor_y
        self._text_atlas_row_height = max(row_h, region_h)
        return (cursor_x, cursor_y)

    def _blit_alpha_to_atlas(
        self,
        *,
        x: int,
        y: int,
        width: int,
        height: int,
        data: bytes,
        pad: int = 0,
    ) -> None:
        atlas_w = max(1, int(self._text_atlas_width))
        atlas_h = max(1, int(self._text_atlas_height))
        if not self._text_atlas_pixels:
            return
        pad_px = int(max(0, pad))
        if (
            x - pad_px < 0
            or y - pad_px < 0
            or x + width + pad_px > atlas_w
            or y + height + pad_px > atlas_h
        ):
            return
        index = 0
        for row in range(height):
            dst_row = y + row
            dst_offset = (dst_row * atlas_w) + x
            row_end = index + width
            self._text_atlas_pixels[dst_offset : dst_offset + width] = data[index:row_end]
            index = row_end
        if pad_px > 0 and width > 0 and height > 0:
            x0 = int(x)
            x1 = int(x + width - 1)
            for row in range(y, y + height):
                row_offset = row * atlas_w
                left_px = self._text_atlas_pixels[row_offset + x0]
                right_px = self._text_atlas_pixels[row_offset + x1]
                for i in range(1, pad_px + 1):
                    self._text_atlas_pixels[row_offset + x0 - i] = left_px
                    self._text_atlas_pixels[row_offset + x1 + i] = right_px
            span_from = x - pad_px
            span_to = x + width + pad_px
            top_row_offset = y * atlas_w
            bottom_row_offset = (y + height - 1) * atlas_w
            top_span = self._text_atlas_pixels[top_row_offset + span_from : top_row_offset + span_to]
            bottom_span = self._text_atlas_pixels[
                bottom_row_offset + span_from : bottom_row_offset + span_to
            ]
            for i in range(1, pad_px + 1):
                dst_top = (y - i) * atlas_w
                dst_bottom = (y + height - 1 + i) * atlas_w
                self._text_atlas_pixels[dst_top + span_from : dst_top + span_to] = top_span
                self._text_atlas_pixels[dst_bottom + span_from : dst_bottom + span_to] = bottom_span
        self._text_atlas_dirty = True

    def _map_design_rect(
        self,
        rect: "_DrawRect",
        *,
        sx: float,
        sy: float,
        ox: float,
        oy: float,
    ) -> "_DrawRect":
        return _DrawRect(
            layer=int(rect.layer),
            x=(float(rect.x) * sx) + ox,
            y=(float(rect.y) * sy) + oy,
            w=max(1.0, float(rect.w) * sx),
            h=max(1.0, float(rect.h) * sy),
            color=rect.color,
        )

    @staticmethod
    def _with_layer(rect: "_DrawRect", layer: int) -> "_DrawRect":
        return _DrawRect(
            layer=int(layer),
            x=float(rect.x),
            y=float(rect.y),
            w=float(rect.w),
            h=float(rect.h),
            color=rect.color,
        )

    def _draw_rect_batches(
        self,
        render_pass: object,
        draw_rects: tuple["_DrawRect", ...],
        *,
        stream_kind: str,
        static_batch_key: tuple[object, ...] | None = None,
    ) -> None:
        set_pipeline = getattr(render_pass, "set_pipeline", None)
        set_vertex_buffer = getattr(render_pass, "set_vertex_buffer", None)
        draw = getattr(render_pass, "draw", None)
        if not callable(set_pipeline) or not callable(set_vertex_buffer) or not callable(draw):
            active_pipeline: object | None = None
            for rect in draw_rects:
                active_pipeline = self._apply_draw_rect(
                    render_pass,
                    rect,
                    active_pipeline=active_pipeline,
                    stream_kind=stream_kind,
                )
            return
        if stream_kind == "static":
            cache_key = (
                ("packet_sig", static_batch_key)
                if static_batch_key is not None
                else _draw_rects_cache_key(draw_rects)
            )
            if (
                cache_key == self._static_draw_cache_key
                and self._draw_vertex_buffer_static is not None
                and self._static_draw_runs
            ):
                self._execute_static_reused_frame = True
                execute_bundles = getattr(render_pass, "execute_bundles", None)
                if (
                    callable(execute_bundles)
                    and self._static_render_bundle is not None
                    and self._static_render_bundle_key == cache_key
                    and self._bundle_replay_enabled_for_draw_count(len(self._static_draw_runs))
                ):
                    execute_bundles([self._static_render_bundle])
                    self._execute_static_bundle_replayed_frame = True
                    self._execute_bundle_replays_frame += 1
                    self._execute_static_run_count_frame += int(len(self._static_draw_runs))
                    return
                set_vertex_buffer(0, self._draw_vertex_buffer_static)
                self._execute_vertex_buffer_binds_frame += 1
                self._execute_static_run_count_frame += int(len(self._static_draw_runs))
                pipeline = self._pipeline_for_color((1.0, 1.0, 1.0, 1.0))
                if pipeline is None:
                    return
                set_pipeline(pipeline)
                self._execute_pipeline_binds_frame += 1
                for run_first_vertex, run_vertex_count in self._static_draw_runs:
                    draw(run_vertex_count, 1, run_first_vertex, 0)
                    self._execute_draw_calls_frame += 1
                return
        packed_vertices = self._batch_vertices_for_rects(draw_rects)
        vertex_buffer, total_vertex_count, uploaded_bytes = self._create_vertex_buffer_from_positions(
            packed_vertices,
            stream_kind=stream_kind,
        )
        if total_vertex_count <= 0:
            return
        run_draws = ((0, int(total_vertex_count)),)
        if stream_kind == "static":
            self._execute_static_upload_bytes_frame += int(uploaded_bytes)
            self._execute_static_rebuild_count_frame += 1
            self._execute_static_run_count_frame += int(len(run_draws))
            cache_key = (
                ("packet_sig", static_batch_key)
                if static_batch_key is not None
                else _draw_rects_cache_key(draw_rects)
            )
            self._static_draw_cache_key = cache_key
            self._static_draw_runs = tuple(run_draws)
            if self._bundle_replay_enabled_for_draw_count(len(run_draws)):
                self._static_render_bundle = self._build_static_render_bundle(
                    run_draws=tuple(run_draws),
                    vertex_buffer=vertex_buffer,
                )
            else:
                self._static_render_bundle = None
            self._static_render_bundle_key = (
                cache_key if self._static_render_bundle is not None else None
            )
        else:
            self._execute_dynamic_upload_bytes_frame += int(uploaded_bytes)
            self._execute_dynamic_run_count_frame += int(len(run_draws))
        if vertex_buffer is None or total_vertex_count <= 0:
            return
        pipeline = self._pipeline_for_color((1.0, 1.0, 1.0, 1.0))
        if pipeline is None:
            return
        set_pipeline(pipeline)
        self._execute_pipeline_binds_frame += 1
        set_vertex_buffer(0, vertex_buffer)
        self._execute_vertex_buffer_binds_frame += 1
        for run_first_vertex, run_vertex_count in run_draws:
            draw(run_vertex_count, 1, run_first_vertex, 0)
            self._execute_draw_calls_frame += 1

    def _draw_text_batches(
        self,
        render_pass: object,
        text_quads: tuple[_DrawTextQuad, ...],
        *,
        stream_kind: str,
        static_batch_key: tuple[object, ...] | None = None,
    ) -> None:
        if not text_quads:
            return
        if not self._supports_text_atlas():
            return
        text_pipeline = self._text_pipeline
        text_bind_group = self._text_bind_group
        if text_pipeline is None or text_bind_group is None:
            return
        set_pipeline = getattr(render_pass, "set_pipeline", None)
        set_bind_group = getattr(render_pass, "set_bind_group", None)
        set_vertex_buffer = getattr(render_pass, "set_vertex_buffer", None)
        draw = getattr(render_pass, "draw", None)
        if (
            not callable(set_pipeline)
            or not callable(set_bind_group)
            or not callable(set_vertex_buffer)
            or not callable(draw)
        ):
            return
        self._upload_text_atlas_if_needed()
        if stream_kind == "static":
            cache_key = (
                ("packet_sig", static_batch_key)
                if static_batch_key is not None
                else _text_quads_cache_key(text_quads)
            )
            if (
                cache_key == self._static_text_cache_key
                and self._draw_text_vertex_buffer_static is not None
                and self._static_text_vertex_count > 0
            ):
                self._execute_static_reused_frame = True
                execute_bundles = getattr(render_pass, "execute_bundles", None)
                if (
                    callable(execute_bundles)
                    and self._static_text_bundle is not None
                    and self._static_text_bundle_key == cache_key
                    and self._bundle_replay_enabled_for_draw_count(1)
                ):
                    execute_bundles([self._static_text_bundle])
                    self._execute_static_bundle_replayed_frame = True
                    self._execute_bundle_replays_frame += 1
                    return
                set_pipeline(text_pipeline)
                self._execute_pipeline_binds_frame += 1
                set_bind_group(0, text_bind_group)
                self._execute_bind_group_binds_frame += 1
                set_vertex_buffer(0, self._draw_text_vertex_buffer_static)
                self._execute_vertex_buffer_binds_frame += 1
                draw(self._static_text_vertex_count, 1, 0, 0)
                self._execute_draw_calls_frame += 1
                return
        vertices = self._text_vertices_for_quads(text_quads)
        text_buffer, vertex_count, uploaded_bytes = self._create_text_vertex_buffer(
            values=vertices,
            stream_kind=stream_kind,
        )
        if stream_kind == "static":
            self._execute_static_upload_bytes_frame += int(uploaded_bytes)
            self._execute_static_rebuild_count_frame += 1
            cache_key = (
                ("packet_sig", static_batch_key)
                if static_batch_key is not None
                else _text_quads_cache_key(text_quads)
            )
            self._static_text_cache_key = cache_key
            self._static_text_vertex_count = int(vertex_count)
            if self._bundle_replay_enabled_for_draw_count(1):
                self._static_text_bundle = self._build_static_text_bundle(
                    vertex_buffer=text_buffer,
                    vertex_count=int(vertex_count),
                )
            else:
                self._static_text_bundle = None
            self._static_text_bundle_key = (
                cache_key if self._static_text_bundle is not None else None
            )
        else:
            self._execute_dynamic_upload_bytes_frame += int(uploaded_bytes)
        if text_buffer is None or vertex_count <= 0:
            return
        set_pipeline(text_pipeline)
        self._execute_pipeline_binds_frame += 1
        set_bind_group(0, text_bind_group)
        self._execute_bind_group_binds_frame += 1
        set_vertex_buffer(0, text_buffer)
        self._execute_vertex_buffer_binds_frame += 1
        draw(vertex_count, 1, 0, 0)
        self._execute_draw_calls_frame += 1

    def _text_vertices_for_quads(self, text_quads: tuple[_DrawTextQuad, ...]) -> list[float]:
        if not text_quads:
            return []
        sorted_quads = tuple(
            sorted(
                text_quads,
                key=lambda quad: (
                    int(quad.layer),
                    round(float(quad.y), 3),
                    round(float(quad.x), 3),
                ),
            )
        )
        out: list[float] = []
        width = max(1.0, float(self._target_width))
        height = max(1.0, float(self._target_height))
        for quad in sorted_quads:
            if float(quad.w) <= 0.0 or float(quad.h) <= 0.0:
                continue
            x0 = (float(quad.x) / width) * 2.0 - 1.0
            x1 = ((float(quad.x) + float(quad.w)) / width) * 2.0 - 1.0
            y0 = 1.0 - ((float(quad.y) / height) * 2.0)
            y1 = 1.0 - (((float(quad.y) + float(quad.h)) / height) * 2.0)
            u0 = float(quad.u0)
            v0 = float(quad.v0)
            u1 = float(quad.u1)
            v1 = float(quad.v1)
            r, g, b, a = quad.color
            out.extend((x0, y0, u0, v0, r, g, b, a))
            out.extend((x1, y0, u1, v0, r, g, b, a))
            out.extend((x0, y1, u0, v1, r, g, b, a))
            out.extend((x0, y1, u0, v1, r, g, b, a))
            out.extend((x1, y0, u1, v0, r, g, b, a))
            out.extend((x1, y1, u1, v1, r, g, b, a))
        return out

    def _create_text_vertex_buffer(
        self,
        *,
        values: list[float],
        stream_kind: str,
    ) -> tuple[object | None, int, int]:
        if not values:
            return None, 0, 0
        raw = _pack_f32_bytes(values)
        buffer = self._ensure_text_vertex_buffer_capacity(
            stream_kind=stream_kind,
            minimum_bytes=len(raw),
        )
        if buffer is None:
            return None, 0, 0
        write_buffer = getattr(self._queue, "write_buffer", None)
        if not callable(write_buffer):
            return None, 0, 0
        try:
            write_buffer(buffer, 0, raw)
        except Exception:
            return None, 0, 0
        return buffer, int(len(values) // 8), int(len(raw))

    def _ensure_text_vertex_buffer_capacity(
        self,
        *,
        stream_kind: str,
        minimum_bytes: int,
    ) -> object | None:
        required = max(256, int(minimum_bytes))
        if stream_kind == "static":
            current = self._draw_text_vertex_buffer_static
            current_cap = int(self._draw_text_vertex_buffer_static_capacity)
        else:
            current = self._draw_text_vertex_buffer_dynamic
            current_cap = int(self._draw_text_vertex_buffer_dynamic_capacity)
        if current is not None and current_cap >= required:
            return current
        create_buffer = getattr(self._device, "create_buffer", None)
        if not callable(create_buffer):
            return None
        usage = _resolve_buffer_usage(self._wgpu)
        capacity = 4096
        while capacity < required:
            capacity *= 2
        try:
            created = create_buffer(size=capacity, usage=usage, mapped_at_creation=False)
        except Exception:
            return None
        if stream_kind == "static":
            self._draw_text_vertex_buffer_static = cast(object, created)
            self._draw_text_vertex_buffer_static_capacity = int(capacity)
        else:
            self._draw_text_vertex_buffer_dynamic = cast(object, created)
            self._draw_text_vertex_buffer_dynamic_capacity = int(capacity)
        return cast(object, created)

    def _build_static_text_bundle(
        self,
        *,
        vertex_buffer: object | None,
        vertex_count: int,
    ) -> object | None:
        if vertex_buffer is None or vertex_count <= 0:
            return None
        if self._text_pipeline is None or self._text_bind_group is None:
            return None
        create_bundle_encoder = getattr(self._device, "create_render_bundle_encoder", None)
        if not callable(create_bundle_encoder):
            return None
        try:
            bundle_encoder = create_bundle_encoder(
                color_formats=[self._surface_format],
                depth_stencil_format=None,
                sample_count=1,
            )
        except Exception:
            return None
        set_pipeline = getattr(bundle_encoder, "set_pipeline", None)
        set_bind_group = getattr(bundle_encoder, "set_bind_group", None)
        set_vertex_buffer = getattr(bundle_encoder, "set_vertex_buffer", None)
        draw = getattr(bundle_encoder, "draw", None)
        finish = getattr(bundle_encoder, "finish", None)
        if (
            not callable(set_pipeline)
            or not callable(set_bind_group)
            or not callable(set_vertex_buffer)
            or not callable(draw)
            or not callable(finish)
        ):
            return None
        try:
            set_pipeline(self._text_pipeline)
            set_bind_group(0, self._text_bind_group)
            set_vertex_buffer(0, vertex_buffer)
            draw(vertex_count, 1, 0, 0)
            return cast(object, finish())
        except Exception:
            return None

    def _bundle_replay_enabled_for_draw_count(self, draw_call_count: int) -> bool:
        return int(draw_call_count) >= int(self._static_bundle_min_draw_calls)

    def _build_static_render_bundle(
        self,
        *,
        run_draws: tuple[tuple[int, int], ...],
        vertex_buffer: object,
    ) -> object | None:
        create_bundle_encoder = getattr(self._device, "create_render_bundle_encoder", None)
        if not callable(create_bundle_encoder):
            return None
        try:
            bundle_encoder = create_bundle_encoder(
                color_formats=[self._surface_format],
                depth_stencil_format=None,
                sample_count=1,
            )
        except Exception:
            return None
        set_pipeline = getattr(bundle_encoder, "set_pipeline", None)
        set_vertex_buffer = getattr(bundle_encoder, "set_vertex_buffer", None)
        draw = getattr(bundle_encoder, "draw", None)
        finish = getattr(bundle_encoder, "finish", None)
        if not callable(set_pipeline) or not callable(set_vertex_buffer) or not callable(draw):
            return None
        if not callable(finish):
            return None
        try:
            set_vertex_buffer(0, vertex_buffer)
            pipeline = self._pipeline_for_color((1.0, 1.0, 1.0, 1.0))
            if pipeline is None:
                return None
            set_pipeline(pipeline)
            for run_first_vertex, run_vertex_count in run_draws:
                draw(run_vertex_count, 1, run_first_vertex, 0)
            return cast(object, finish())
        except Exception:
            return None

    def _prime_native_paths(self) -> None:
        if not get_runtime_config().renderer.prime_native_paths:
            return
        write_buffer = getattr(self._queue, "write_buffer", None)
        if not callable(write_buffer):
            return
        try:
            raw = _pack_f32_bytes([0.0] * 12)
            draw_buffer = self._ensure_draw_vertex_buffer_capacity(
                stream_kind="dynamic",
                minimum_bytes=len(raw),
            )
            if draw_buffer is not None:
                write_buffer(draw_buffer, 0, raw)
            text_raw = _pack_f32_bytes([0.0] * 16)
            text_buffer = self._ensure_text_vertex_buffer_capacity(
                stream_kind="dynamic",
                minimum_bytes=len(text_raw),
            )
            if text_buffer is not None:
                write_buffer(text_buffer, 0, text_raw)
        except Exception:
            return

    def _prime_text_paths(self) -> None:
        renderer_config = get_runtime_config().renderer
        if not renderer_config.text_prewarm_enabled:
            return
        if not self._supports_text_atlas():
            return
        sizes = [int(value) for value in renderer_config.text_prewarm_sizes]
        if not sizes:
            sizes = [14, 18, 24]
        seed_text = str(renderer_config.text_prewarm_chars)[
            : int(renderer_config.text_prewarm_max_chars)
        ].strip()
        labels: list[str] = []
        for label in renderer_config.text_prewarm_labels:
            value = label.strip()
            if value:
                labels.append(value)
        if not seed_text and not labels:
            return
        for size in sizes:
            if seed_text:
                try:
                    self._layout_glyph_run(text=seed_text, font_size_px=int(size))
                except Exception:
                    continue
            for label in labels:
                try:
                    self._layout_glyph_run(text=label, font_size_px=int(size))
                except Exception:
                    continue
        try:
            self._upload_text_atlas_if_needed()
        except Exception:
            return

    def _prime_startup_render_paths(self) -> None:
        renderer_config = get_runtime_config().renderer
        if not renderer_config.startup_prewarm_enabled:
            return
        frames = max(1, int(renderer_config.startup_prewarm_frames))
        packets = self._startup_prewarm_packets()
        if not packets:
            return
        for _ in range(frames):
            try:
                self.begin_frame()
                self.draw_packets(
                    "overlay",
                    packets,
                    pass_signature=("engine_startup_prewarm",),
                )
                self.present()
            except Exception:
                break
            finally:
                if self._frame_in_flight:
                    self.end_frame()

    def _startup_prewarm_packets(self) -> tuple[_DrawPacket, ...]:
        text_color = (1.0, 1.0, 1.0, 1.0)
        return (
            _DrawPacket(
                kind="fill_window",
                layer=-10000,
                sort_key="prewarm.fill",
                transform=(),
                data=(("color", "#0f1117"), ("key", "__prewarm_fill")),
            ),
            _DrawPacket(
                kind="rect",
                layer=10,
                sort_key="prewarm.rect",
                transform=(),
                data=(
                    ("x", 64.0),
                    ("y", 64.0),
                    ("w", 360.0),
                    ("h", 120.0),
                    ("linear_rgba", (0.18, 0.33, 0.92, 1.0)),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "rect", 1)),
                ),
            ),
            _DrawPacket(
                kind="rounded_rect",
                layer=20,
                sort_key="prewarm.rounded",
                transform=(),
                data=(
                    ("x", 480.0),
                    ("y", 64.0),
                    ("w", 360.0),
                    ("h", 120.0),
                    ("radius", 14.0),
                    ("linear_rgba", (0.78, 0.21, 0.28, 1.0)),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "rounded", 1)),
                ),
            ),
            _DrawPacket(
                kind="stroke_rect",
                layer=30,
                sort_key="prewarm.stroke",
                transform=(),
                data=(
                    ("x", 64.0),
                    ("y", 220.0),
                    ("w", 776.0),
                    ("h", 120.0),
                    ("thickness", 2.0),
                    ("linear_rgba", (0.94, 0.95, 0.97, 1.0)),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "stroke", 1)),
                ),
            ),
            _DrawPacket(
                kind="shadow_rect",
                layer=35,
                sort_key="prewarm.shadow",
                transform=(),
                data=(
                    ("x", 64.0),
                    ("y", 220.0),
                    ("w", 776.0),
                    ("h", 120.0),
                    ("radius", 2.0),
                    ("thickness", 4.0),
                    ("linear_rgba", (0.0, 0.0, 0.0, 0.4)),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "shadow", 1)),
                ),
            ),
            _DrawPacket(
                kind="text",
                layer=40,
                sort_key="prewarm.text",
                transform=(),
                data=(
                    ("text", "Generate Random Fleet"),
                    ("font_size", 24.0),
                    ("x", 96.0),
                    ("y", 96.0),
                    ("anchor", "top-left"),
                    ("linear_rgba", text_color),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "text", 1)),
                ),
            ),
            _DrawPacket(
                kind="title",
                layer=50,
                sort_key="prewarm.title",
                transform=(),
                data=(
                    ("text", "WARSHIPS 2"),
                    ("font_size", 36.0),
                    ("x", 96.0),
                    ("y", 250.0),
                    ("anchor", "top-left"),
                    ("linear_rgba", text_color),
                    ("_engine_static", True),
                    ("_engine_version", ("prewarm", "title", 1)),
                ),
            ),
        )

    def _batch_vertices_for_rects(self, rects: tuple["_DrawRect", ...]) -> list[float]:
        vertices: list[float] = []
        for rect in rects:
            vertices.extend(self._clip_vertices_for_rect(rect))
        return vertices

    def _clip_vertices_for_rect(self, rect: "_DrawRect") -> tuple[float, ...]:
        width = max(1.0, float(self._target_width))
        height = max(1.0, float(self._target_height))
        rx = max(0.0, min(width, float(rect.x)))
        ry = max(0.0, min(height, float(rect.y)))
        rw = max(1.0, min(width - rx, float(rect.w)))
        rh = max(1.0, min(height - ry, float(rect.h)))
        x0 = (rx / width) * 2.0 - 1.0
        x1 = ((rx + rw) / width) * 2.0 - 1.0
        y0 = 1.0 - ((ry / height) * 2.0)
        y1 = 1.0 - (((ry + rh) / height) * 2.0)
        r, g, b, a = rect.color
        return (
            x0, y0, r, g, b, a,
            x1, y0, r, g, b, a,
            x0, y1, r, g, b, a,
            x0, y1, r, g, b, a,
            x1, y0, r, g, b, a,
            x1, y1, r, g, b, a,
        )

    def _create_vertex_buffer_from_positions(
        self,
        values: list[float],
        *,
        stream_kind: str,
    ) -> tuple[object | None, int, int]:
        if not values:
            return None, 0, 0
        raw = _pack_f32_bytes(values)
        buffer = self._ensure_draw_vertex_buffer_capacity(
            stream_kind=stream_kind,
            minimum_bytes=len(raw),
        )
        if buffer is None:
            return None, 0, 0
        write_buffer = getattr(self._queue, "write_buffer", None)
        if callable(write_buffer):
            try:
                write_buffer(buffer, 0, raw)
            except Exception:
                return None, 0, 0
        else:
            return None, 0, 0
        return buffer, int(len(values) // 6), int(len(raw))

    def _apply_draw_rect(
        self,
        render_pass: object,
        rect: "_DrawRect",
        *,
        active_pipeline: object | None = None,
        stream_kind: str = "dynamic",
    ) -> object | None:
        set_pipeline = getattr(render_pass, "set_pipeline", None)
        set_vertex_buffer = getattr(render_pass, "set_vertex_buffer", None)
        draw = getattr(render_pass, "draw", None)
        if not callable(set_vertex_buffer) or not callable(draw):
            return active_pipeline
        pipeline = self._pipeline_for_color(rect.color)
        if callable(set_pipeline) and pipeline is not None and pipeline is not active_pipeline:
            set_pipeline(pipeline)
        vertices = self._clip_vertices_for_rect(rect)
        vertex_buffer, vertex_count, _uploaded_bytes = self._create_vertex_buffer_from_positions(
            list(vertices),
            stream_kind=stream_kind,
        )
        if vertex_buffer is None or vertex_count <= 0:
            return pipeline if pipeline is not None else active_pipeline
        set_vertex_buffer(0, vertex_buffer)
        draw(vertex_count, 1, 0, 0)
        return pipeline if pipeline is not None else active_pipeline

    def consume_execute_telemetry(self) -> dict[str, object]:
        payload = {
            "execute_static_reused": bool(self._execute_static_reused_frame),
            "execute_static_bundle_replayed": bool(self._execute_static_bundle_replayed_frame),
            "execute_static_upload_bytes": int(self._execute_static_upload_bytes_frame),
            "execute_dynamic_upload_bytes": int(self._execute_dynamic_upload_bytes_frame),
            "execute_static_rebuild_count": int(self._execute_static_rebuild_count_frame),
            "execute_static_run_count": int(self._execute_static_run_count_frame),
            "execute_dynamic_run_count": int(self._execute_dynamic_run_count_frame),
            "execute_stage_upload_ms": float(max(0.0, self._execute_stage_upload_ms_frame)),
            "execute_translate_ms": float(max(0.0, self._execute_translate_ms_frame)),
            "execute_expand_ms": float(max(0.0, self._execute_expand_ms_frame)),
            "execute_draw_packets_total_ms": float(
                max(0.0, self._execute_draw_packets_total_ms_frame)
            ),
            "execute_packet_preprocess_ms": float(
                max(0.0, self._execute_packet_preprocess_ms_frame)
            ),
            "execute_static_key_build_ms": float(
                max(0.0, self._execute_static_key_build_ms_frame)
            ),
            "execute_begin_render_pass_ms": float(
                max(0.0, self._execute_begin_render_pass_ms_frame)
            ),
            "execute_render_pass_record_ms": float(
                max(0.0, self._execute_render_pass_record_ms_frame)
            ),
            "execute_render_pass_end_ms": float(max(0.0, self._execute_render_pass_end_ms_frame)),
            "execute_rect_batch_ms": float(max(0.0, self._execute_rect_batch_ms_frame)),
            "execute_text_batch_ms": float(max(0.0, self._execute_text_batch_ms_frame)),
            "execute_text_layout_ms": float(max(0.0, self._execute_text_layout_ms_frame)),
            "execute_text_shape_ms": float(max(0.0, self._execute_text_shape_ms_frame)),
            "execute_text_shape_calls": int(self._execute_text_shape_calls_frame),
            "execute_atlas_upload_ms": float(max(0.0, self._execute_atlas_upload_ms_frame)),
            "execute_atlas_upload_bytes": int(self._execute_atlas_upload_bytes_frame),
            "execute_atlas_upload_count": int(self._execute_atlas_upload_count_frame),
            "execute_packet_translate_count": int(self._execute_packet_translate_count_frame),
            "execute_rect_count": int(self._execute_rect_count_frame),
            "execute_text_quad_count": int(self._execute_text_quad_count_frame),
            "execute_draw_calls": int(self._execute_draw_calls_frame),
            "execute_pipeline_binds": int(self._execute_pipeline_binds_frame),
            "execute_vertex_buffer_binds": int(self._execute_vertex_buffer_binds_frame),
            "execute_bind_group_binds": int(self._execute_bind_group_binds_frame),
            "execute_bundle_replays": int(self._execute_bundle_replays_frame),
            "present_mode": str(self._present_mode),
            "execute_kind_rect_counts": dict(sorted(self._execute_kind_rect_counts_frame.items())),
            "execute_kind_text_quad_counts": dict(
                sorted(self._execute_kind_text_quad_counts_frame.items())
            ),
        }
        if self._cffi_miss_diagnostics_enabled and self._cffi_miss_store is not None:
            total = int(sum(int(v) for v in self._cffi_miss_store.values()))
            delta = int(max(0, total - int(self._cffi_miss_total_last)))
            self._cffi_miss_total_last = total
            sorted_items = sorted(
                ((str(name), int(count)) for name, count in self._cffi_miss_store.items()),
                key=lambda item: item[1],
                reverse=True,
            )
            payload["execute_cffi_type_miss_total"] = int(total)
            payload["execute_cffi_type_miss_delta"] = int(delta)
            payload["execute_cffi_type_miss_unique"] = int(len(sorted_items))
            payload["execute_cffi_type_miss_top"] = dict(sorted_items[:8])
        return payload

    def _ensure_draw_vertex_buffer_capacity(
        self,
        *,
        stream_kind: str,
        minimum_bytes: int,
    ) -> object | None:
        required = max(256, int(minimum_bytes))
        if stream_kind == "static":
            current_buffer = self._draw_vertex_buffer_static
            current_capacity = int(self._draw_vertex_buffer_static_capacity)
        else:
            current_buffer = self._draw_vertex_buffer_dynamic
            current_capacity = int(self._draw_vertex_buffer_dynamic_capacity)
        if current_buffer is not None and current_capacity >= required:
            return current_buffer
        create_buffer = getattr(self._device, "create_buffer", None)
        if not callable(create_buffer):
            return None
        usage = _resolve_buffer_usage(self._wgpu)
        capacity = 4096
        while capacity < required:
            capacity *= 2
        try:
            buffer = create_buffer(size=capacity, usage=usage, mapped_at_creation=False)
        except Exception:
            return None
        if stream_kind == "static":
            self._draw_vertex_buffer_static = cast(object, buffer)
            self._draw_vertex_buffer_static_capacity = int(capacity)
        else:
            self._draw_vertex_buffer_dynamic = cast(object, buffer)
            self._draw_vertex_buffer_dynamic_capacity = int(capacity)
        return cast(object, buffer)


def _resolve_texture_usage(wgpu_mod: object) -> int:
    texture_usage = getattr(wgpu_mod, "TextureUsage", None)
    if texture_usage is None:
        return 0x10 | 0x04  # RENDER_ATTACHMENT | COPY_SRC (fallback)
    render_attachment = int(getattr(texture_usage, "RENDER_ATTACHMENT", 0x10))
    copy_src = int(getattr(texture_usage, "COPY_SRC", 0x04))
    return render_attachment | copy_src


def _packet_is_static(packet: _DrawPacket) -> bool:
    raw_engine_static = getattr(packet, "engine_static", None)
    if isinstance(raw_engine_static, bool):
        return raw_engine_static
    raw_data = getattr(packet, "data", ())
    if not isinstance(raw_data, tuple):
        return False
    engine_static = _packet_data_value(raw_data, "_engine_static")
    if isinstance(engine_static, bool):
        return bool(engine_static)
    for item in raw_data:
        if not (isinstance(item, tuple) and len(item) == 2):
            continue
        key, value = item
        if str(key) != "static":
            continue
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False
    return False


def _packet_static_override(packet: _DrawPacket) -> str:
    raw_data = getattr(packet, "data", ())
    if not isinstance(raw_data, tuple):
        return "auto"
    override_raw = _packet_data_value(raw_data, "static")
    if isinstance(override_raw, bool):
        return "force_static" if override_raw else "auto"
    if isinstance(override_raw, (int, float)):
        return "force_static" if bool(override_raw) else "auto"
    if isinstance(override_raw, str):
        value = override_raw.strip().lower()
        if value in {"1", "true", "yes", "on", "static", "force_static"}:
            return "force_static"
        if value in {"dynamic", "force_dynamic", "0", "false", "off"}:
            return "force_dynamic"
    return "auto"


def _packet_key(packet: _DrawPacket) -> str | None:
    raw_data = getattr(packet, "data", ())
    if not isinstance(raw_data, tuple):
        return None
    raw = _packet_data_value(raw_data, "key")
    if raw is None:
        return None
    value = str(raw).strip()
    return value if value else None


def _packet_fingerprint(packet: _DrawPacket) -> tuple[object, ...]:
    version_token = _packet_version_token(packet)
    if version_token is None:
        version_token = (int(id(packet.data)), int(id(packet.transform)))
    version_key = _version_fingerprint(version_token)
    return (
        str(packet.kind),
        int(packet.layer),
        str(packet.sort_key),
        version_key,
    )


def _packet_version_token(packet: _DrawPacket) -> object | None:
    raw_engine_version = getattr(packet, "engine_version", None)
    if raw_engine_version is not None:
        return cast(object, raw_engine_version)
    raw_data = getattr(packet, "data", ())
    if not isinstance(raw_data, tuple):
        return None
    return _packet_data_value(raw_data, "_engine_version")


def _version_fingerprint(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str, bytes)):
        return value
    try:
        return ("h", int(hash(value)))
    except Exception:
        return ("id", int(id(value)))


def _static_packet_identity(packet: _DrawPacket) -> tuple[object, ...]:
    version_token = _packet_version_token(packet)
    if version_token is None:
        version_token = (int(id(packet.data)), int(id(packet.transform)))
    return (
        str(packet.kind),
        int(packet.layer),
        str(packet.sort_key),
        _version_fingerprint(version_token),
        packet.data,
        packet.transform,
    )


def _packet_data_value(raw_data: tuple[tuple[str, object], ...], key_name: str) -> object | None:
    for item in raw_data:
        if not (isinstance(item, tuple) and len(item) == 2):
            continue
        key, value = item
        if str(key) == key_name:
            return value
    return None


def _freeze_packet_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, tuple):
        return tuple(_freeze_packet_value(item) for item in value)
    if isinstance(value, list):
        return tuple(_freeze_packet_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), _freeze_packet_value(item)) for key, item in value.items())
        )
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze_packet_value(item) for item in value), key=str))
    return repr(value)


def _draw_rects_cache_key(draw_rects: tuple[_DrawRect, ...]) -> tuple[object, ...]:
    if not draw_rects:
        return ()
    return (len(draw_rects), hash(draw_rects))


def _text_quads_cache_key(text_quads: tuple[_DrawTextQuad, ...]) -> tuple[object, ...]:
    if not text_quads:
        return ()
    return (len(text_quads), hash(text_quads))


def _resolve_buffer_usage(wgpu_mod: object) -> int:
    buffer_usage = getattr(wgpu_mod, "BufferUsage", None)
    if buffer_usage is None:
        return 0x80 | 0x20  # VERTEX | COPY_DST fallback
    vertex = int(getattr(buffer_usage, "VERTEX", 0x80))
    copy_dst = int(getattr(buffer_usage, "COPY_DST", 0x20))
    return vertex | copy_dst


def _resolve_text_texture_usage(wgpu_mod: object) -> int:
    texture_usage = getattr(wgpu_mod, "TextureUsage", None)
    if texture_usage is None:
        return 0x04 | 0x08  # TEXTURE_BINDING | COPY_DST fallback
    texture_binding = int(getattr(texture_usage, "TEXTURE_BINDING", 0x04))
    copy_dst = int(getattr(texture_usage, "COPY_DST", 0x08))
    return texture_binding | copy_dst


def _pack_f32_bytes(values: list[float]) -> bytes:
    if not values:
        return b""
    if _NP is None:
        raise RuntimeError("numpy is required for native float packing path")
    arr = _NP.asarray(values, dtype=_NP.float32)
    return bytes(arr.tobytes(order="C"))


def _resolve_backend_priority() -> tuple[str, ...]:
    values = tuple(item.strip().lower() for item in get_runtime_config().bootstrap.wgpu_backends)
    return values or ("vulkan", "metal", "dx12")


def _env_flag(name: str, default: bool) -> bool:
    runtime_config = get_runtime_config()
    mapping: dict[str, bool] = {
        "ENGINE_DIAGNOSTICS_RENDER_STAGE_EVENTS_ENABLED": runtime_config.renderer.diag_stage_events_enabled,
        "ENGINE_WGPU_PRIME_NATIVE_PATHS": runtime_config.renderer.prime_native_paths,
        "ENGINE_WGPU_TEXT_PREWARM_ENABLED": runtime_config.renderer.text_prewarm_enabled,
        "ENGINE_WGPU_STARTUP_PREWARM_ENABLED": runtime_config.renderer.startup_prewarm_enabled,
        "ENGINE_WGPU_CFFI_FASTPATH_ENABLED": True,
        "ENGINE_WGPU_CFFI_PREWARM_ENABLED": True,
    }
    return bool(mapping.get(name, bool(default)))


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    runtime_config = get_runtime_config()
    mapping: dict[str, int] = {
        "ENGINE_DIAGNOSTICS_RENDER_STAGE_SAMPLING_N": runtime_config.renderer.diag_stage_sampling_n,
        "ENGINE_DIAGNOSTICS_RENDER_PROFILE_SAMPLING_N": runtime_config.renderer.diag_profile_sampling_n,
        "ENGINE_RENDER_AUTO_STATIC_MIN_STABLE_FRAMES": runtime_config.renderer.auto_static_min_stable_frames,
        "ENGINE_WGPU_TEXT_PREWARM_MAX_CHARS": runtime_config.renderer.text_prewarm_max_chars,
        "ENGINE_WGPU_STARTUP_PREWARM_FRAMES": runtime_config.renderer.startup_prewarm_frames,
        "ENGINE_UI_DESIGN_WIDTH": runtime_config.render.ui_design_width,
        "ENGINE_UI_DESIGN_HEIGHT": runtime_config.render.ui_design_height,
        "ENGINE_WGPU_RECOVERY_FAILURE_STREAK_THRESHOLD": runtime_config.renderer.recovery_failure_streak_threshold,
        "ENGINE_WGPU_RECOVERY_MAX_RETRY_LIMIT": runtime_config.renderer.recovery_max_retry_limit,
        "ENGINE_RENDER_STATIC_BUNDLE_MIN_DRAWS": runtime_config.renderer.static_bundle_min_draws,
        "ENGINE_RENDER_STATIC_PASS_EXPAND_CACHE_MAX": runtime_config.renderer.static_pass_expand_cache_max,
        "ENGINE_WGPU_CFFI_FASTPATH_CACHE_MAX": 512,
        "ENGINE_WGPU_CFFI_PREWARM_MAX_TYPES": 256,
        "ENGINE_WGPU_CFFI_PREWARM_MAX_LITERALS": 2048,
    }
    value = int(mapping.get(name, int(default)))
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    runtime_config = get_runtime_config()
    mapping: dict[str, float] = {
        "ENGINE_RENDER_INTERNAL_SCALE": runtime_config.renderer.internal_scale,
        "ENGINE_WGPU_RECOVERY_COOLDOWN_MS": runtime_config.renderer.recovery_cooldown_ms,
    }
    value = float(mapping.get(name, float(default)))
    return max(float(minimum), float(value))


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return int(default)
    return int(default)


def _resolve_ui_design_dimensions(
    *, default_width: int, default_height: int, runtime_config: RuntimeConfig | None = None
) -> tuple[int, int]:
    config = runtime_config or get_runtime_config()
    if config.render.ui_resolution is not None:
        return (int(config.render.ui_resolution[0]), int(config.render.ui_resolution[1]))
    design_w = max(1, int(config.render.ui_design_width))
    design_h = max(1, int(config.render.ui_design_height))
    if design_w <= 0 or design_h <= 0:
        return (max(1, int(default_width)), max(1, int(default_height)))
    return (design_w, design_h)


def _resolve_system_font_path(*, runtime_config: RuntimeConfig | None = None) -> str:
    checked: list[str] = []
    for candidate in _iter_system_font_candidates(runtime_config=runtime_config):
        normalized = os.path.normpath(candidate)
        checked.append(normalized)
        if os.path.isfile(normalized):
            return normalized
    raise WgpuInitError(
        "system font discovery failed",
        details={
            "selected_backend": "unknown",
            "adapter_info": {},
            "font_candidates_checked": tuple(checked[:64]),
        },
    )


def _iter_system_font_candidates(*, runtime_config: RuntimeConfig | None = None) -> tuple[str, ...]:
    candidates: list[str] = []
    config = runtime_config or get_runtime_config()
    if config.renderer.font_paths:
        candidates.extend(str(item) for item in config.renderer.font_paths if str(item).strip())
        return tuple(candidates)
    candidates.extend(_platform_font_file_candidates())
    for directory in _platform_font_directories():
        if not os.path.isdir(directory):
            continue
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name.lower())
        except Exception:
            continue
        for entry in entries:
            if not entry.is_file():
                continue
            name = entry.name.lower()
            if name.endswith((".ttf", ".otf", ".ttc")):
                candidates.append(entry.path)
    return tuple(candidates)


def _platform_font_file_candidates() -> tuple[str, ...]:
    if os.name == "nt":
        return (
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        )
    if os.name == "posix":
        if sys.platform == "darwin":
            return (
                "/System/Library/Fonts/SFNS.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
            )
        return (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        )
    return ()


def _platform_font_directories() -> tuple[str, ...]:
    if os.name == "nt":
        return (r"C:\Windows\Fonts",)
    if os.name == "posix":
        if sys.platform == "darwin":
            return (
                "/System/Library/Fonts",
                "/System/Library/Fonts/Supplemental",
                "/Library/Fonts",
            )
        return (
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
        )
    return ()


def _patch_wgpu_native_struct_alloc_fastpath() -> None:
    if not _env_flag("ENGINE_WGPU_CFFI_FASTPATH_ENABLED", True):
        return
    try:
        import wgpu.backends.wgpu_native._api as native_api
    except Exception:
        return
    if bool(getattr(native_api, "_engine_struct_alloc_patched", False)):
        return
    ffi = getattr(native_api, "ffi", None)
    original_new_struct_p = getattr(native_api, "_new_struct_p", None)
    original_new_array = getattr(native_api, "new_array", None)
    if ffi is None or not callable(original_new_struct_p) or not callable(original_new_array):
        return
    ctype_cache: dict[str, object] = {}
    ctype_misses: dict[str, int] = {}
    cache_max = max(64, _env_int("ENGINE_WGPU_CFFI_FASTPATH_CACHE_MAX", 512, minimum=64))

    def _new_struct_p_cached(ctype: str, **kwargs: object) -> object:
        ctype_obj = ctype_cache.get(ctype)
        if ctype_obj is None:
            ctype_misses[ctype] = int(ctype_misses.get(ctype, 0)) + 1
            ctype_obj = ffi.typeof(ctype)
            ctype_cache[ctype] = ctype_obj
            while len(ctype_cache) > cache_max:
                first_key = next(iter(ctype_cache))
                if first_key == ctype:
                    break
                ctype_cache.pop(first_key, None)
        struct_p = ffi.new(ctype_obj)
        cstructfield2enum = getattr(native_api, "cstructfield2enum")
        cstructfield2enum_alt = getattr(native_api, "_cstructfield2enum_alt")
        enummap = getattr(native_api, "enummap")
        for key, val in kwargs.items():
            if val is None:
                continue
            if isinstance(val, str) and isinstance(getattr(struct_p, key), int):
                if key in cstructfield2enum_alt:
                    structname = cstructfield2enum_alt[key]
                else:
                    structname = cstructfield2enum[ctype.strip(" *")[4:] + "." + key]
                ival = enummap[structname + "." + val]
                setattr(struct_p, key, ival)
            else:
                setattr(struct_p, key, val)
        return struct_p

    def _new_array_cached(ctype: str, elements: object) -> object:
        assert ctype.endswith("[]")
        ctype_obj = ctype_cache.get(ctype)
        if ctype_obj is None:
            ctype_misses[ctype] = int(ctype_misses.get(ctype, 0)) + 1
            ctype_obj = ffi.typeof(ctype)
            ctype_cache[ctype] = ctype_obj
            while len(ctype_cache) > cache_max:
                first_key = next(iter(ctype_cache))
                if first_key == ctype:
                    break
                ctype_cache.pop(first_key, None)
        if isinstance(elements, int):
            return ffi.new(ctype_obj, elements)
        if elements:
            elements_seq = cast(Any, elements)
            array = ffi.new(ctype_obj, elements)
            refs_per_struct = getattr(native_api, "_refs_per_struct")
            refs_per_struct[array] = [
                refs_per_struct.get(el, None)
                for el in elements_seq
                if isinstance(el, ffi.CData)
            ]
            return array
        return ffi.NULL

    setattr(native_api, "_new_struct_p", _new_struct_p_cached)
    setattr(native_api, "new_array", _new_array_cached)
    setattr(native_api, "_engine_struct_alloc_patched", True)
    setattr(native_api, "_engine_struct_alloc_cache", ctype_cache)
    setattr(native_api, "_engine_struct_alloc_misses", ctype_misses)


def _prewarm_wgpu_native_cffi_types() -> None:
    if not _env_flag("ENGINE_WGPU_CFFI_PREWARM_ENABLED", True):
        return
    try:
        import wgpu.backends.wgpu_native._api as native_api
    except Exception:
        return
    ffi = getattr(native_api, "ffi", None)
    structs_mod = getattr(native_api, "structs", None)
    if ffi is None or structs_mod is None:
        return
    max_types = max(32, _env_int("ENGINE_WGPU_CFFI_PREWARM_MAX_TYPES", 256, minimum=32))
    names = sorted(
        name
        for name in dir(structs_mod)
        if name.endswith("Struct") and len(name) > len("Struct") and name[0].isupper()
    )[:max_types]
    for name in names:
        base = f"WGPU{name[:-6]}"
        for ctype in (f"{base} *", f"{base}[]"):
            try:
                ffi.typeof(ctype)
            except Exception:
                continue
    for ctype in (
        "WGPUChainedStruct *",
        "WGPUChainedStruct * ",
        "char []",
        "intptr_t",
        "uint32_t *",
        "uint32_t []",
        "uint8_t *",
        "uint8_t[]",
        "void *",
    ):
        try:
            ffi.typeof(ctype)
        except Exception:
            continue
    literal_max = max(128, _env_int("ENGINE_WGPU_CFFI_PREWARM_MAX_LITERALS", 2048, minimum=128))
    for ctype in _discover_wgpu_native_ctype_literals(native_api)[:literal_max]:
        try:
            ffi.typeof(ctype)
        except Exception:
            continue


def _discover_wgpu_native_ctype_literals(native_api: object) -> tuple[str, ...]:
    source_path = str(getattr(native_api, "__file__", "")).strip()
    if not source_path or not os.path.exists(source_path):
        return ()
    try:
        with open(source_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except Exception:
        return ()
    # Capture literal ctypes used in ffi.new/new_array/new_struct*/ffi.cast/ffi.typeof.
    pattern = re.compile(
        r"""(?x)
        (?:ffi\.(?:new|cast|typeof)\s*\(\s*|new_array\s*\(\s*|new_struct(?:_p)?\s*\(\s*)
        ["']([^"']+)["']
        """
    )
    out: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        raw = str(match.group(1)).strip()
        if not raw:
            continue
        if " " not in raw and "*" not in raw and "[" not in raw:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return tuple(out)


def _resolve_wgpu_native_cffi_miss_store() -> dict[str, int] | None:
    try:
        import wgpu.backends.wgpu_native._api as native_api
    except Exception:
        return None
    raw = getattr(native_api, "_engine_struct_alloc_misses", None)
    if not isinstance(raw, dict):
        return None
    out: dict[str, int] = {}
    for key, value in raw.items():
        out[str(key)] = int(value) if isinstance(value, int) else 0
    return out


def _ortho_projection(*, width: float, height: float) -> tuple[float, ...]:
    w = max(1.0, float(width))
    h = max(1.0, float(height))
    return (
        2.0 / w,
        0.0,
        0.0,
        -1.0,
        0.0,
        -2.0 / h,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )


_GEOMETRY_WGSL = """
struct VsIn {
    @location(0) pos: vec2<f32>,
    @location(1) color: vec4<f32>,
};

struct VsOut {
    @builtin(position) position: vec4<f32>,
    @location(0) color: vec4<f32>,
};

@vertex
fn vs_main(input: VsIn) -> VsOut {
    var out: VsOut;
    out.position = vec4<f32>(input.pos, 0.0, 1.0);
    out.color = input.color;
    return out;
}

@fragment
fn fs_main(input: VsOut) -> @location(0) vec4<f32> {
    return input.color;
}
"""


_TEXT_WGSL = """
struct VsIn {
    @location(0) pos: vec2<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) color: vec4<f32>,
};

struct VsOut {
    @builtin(position) position: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) color: vec4<f32>,
};

@group(0) @binding(0) var atlas_tex: texture_2d<f32>;
@group(0) @binding(1) var atlas_sampler: sampler;

@vertex
fn vs_main(input: VsIn) -> VsOut {
    var out: VsOut;
    out.position = vec4<f32>(input.pos, 0.0, 1.0);
    out.uv = input.uv;
    out.color = input.color;
    return out;
}

@fragment
fn fs_main(input: VsOut) -> @location(0) vec4<f32> {
    let alpha = textureSample(atlas_tex, atlas_sampler, input.uv).r;
    return vec4<f32>(input.color.rgb, input.color.a * alpha);
}
"""


__all__ = ["WgpuInitError", "WgpuRenderer"]

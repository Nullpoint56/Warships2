"""WGPU-backed renderer implementation scaffold."""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol

from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.api.window import SurfaceHandle, WindowResizeEvent

if TYPE_CHECKING:
    from engine.diagnostics.hub import DiagnosticHub


class _Backend(Protocol):
    """Private backend contract for the renderer internals."""

    def begin_frame(self) -> None:
        """Prepare one backend frame."""

    def draw_packets(self, pass_name: str, packets: tuple["_DrawPacket", ...]) -> None:
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


@dataclass(slots=True)
class WgpuRenderer:
    """Renderer scaffold using immutable snapshots and explicit stages."""

    surface: SurfaceHandle | None = None
    width: int = 1200
    height: int = 720
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

    def __post_init__(self) -> None:
        self._owner_thread_id = int(threading.get_ident())
        factory = self._backend_factory or _create_wgpu_backend
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
        if self._frame_dirty and not self._frame_presented:
            composed = self._compose_frame_snapshot(RenderSnapshot(frame_index=self._frame_index, passes=()))
            batches = self._build_pass_batches(composed)
            self._emit_render_stage(
                "build_batches",
                value={"pass_count": int(len(batches))},
            )
            self._execute_pass_batches(batches)
            self._emit_render_stage("execute_passes")
            self._backend.present()
            self._emit_render_stage("present")
            self._frame_presented = True
            self._frame_dirty = False
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
        return (float(x), float(y))

    def invalidate(self) -> None:
        return

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
        self._backend.close()

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        self._assert_owner_thread()
        started_here = not self._frame_active
        if started_here:
            self.begin_frame()
        try:
            composed = self._compose_frame_snapshot(snapshot)
            batches = self._build_pass_batches(composed)
            self._emit_render_stage(
                "build_batches",
                value={"pass_count": int(len(batches))},
            )
            self._execute_pass_batches(batches)
            self._emit_render_stage("execute_passes")
            self._backend.present()
            self._emit_render_stage("present")
            self._frame_presented = True
            self._frame_dirty = False
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
            indexed_commands = tuple(enumerate(render_pass.commands))
            sorted_indexed = tuple(
                sorted(
                    indexed_commands,
                    key=lambda indexed: _command_sort_key(indexed[1], indexed[0]),
                )
            )
            commands = tuple(command for _, command in sorted_indexed)
            batches.append(_RenderPassBatch(name=descriptor.canonical_name, commands=commands))
        return tuple(sorted(batches, key=lambda batch: _resolve_pass_descriptor(batch.name).priority))

    def _execute_pass_batches(self, batches: tuple[_RenderPassBatch, ...]) -> None:
        for batch in batches:
            packets = tuple(_command_to_packet(command) for command in batch.commands)
            self._emit_render_stage(
                "execute_pass.begin",
                metadata={"pass_name": batch.name, "packet_count": len(packets)},
            )
            self._backend.draw_packets(batch.name, packets)
            self._emit_render_stage(
                "execute_pass.end",
                metadata={"pass_name": batch.name, "packet_count": len(packets)},
            )

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
        hub.emit_fast(
            category="render",
            name=f"render.stage.{stage}",
            tick=self._frame_index,
            value=value,
            metadata=metadata,
        )

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
    payload = {str(key): value for key, value in command.data}
    key = payload.get("key")
    if not isinstance(key, str):
        return ""
    normalized = key.strip()
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
    payload = tuple((str(key), value) for key, value in command.data)
    srgb_rgba = _extract_srgb_rgba(payload)
    linear_rgba = _srgb_to_linear_rgba(srgb_rgba)
    return _DrawPacket(
        kind=str(command.kind),
        layer=int(command.layer),
        sort_key=str(command.sort_key),
        transform=tuple(float(value) for value in command.transform.values),
        data=payload + (("srgb_rgba", srgb_rgba), ("linear_rgba", linear_rgba)),
    )


def _create_wgpu_backend(surface: SurfaceHandle | None) -> _Backend:
    return _WgpuBackend(surface=surface)


def _command_sort_key(command: RenderCommand, ordinal: int) -> tuple[object, ...]:
    return (
        int(command.layer),
        str(command.sort_key),
        str(command.kind),
        _command_key(command),
        tuple((str(key), _stable_sort_value(value)) for key, value in command.data),
        tuple(_stable_sort_value(float(value)) for value in command.transform.values),
        int(ordinal),
    )


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
    if isinstance(color_value, str):
        parsed = _parse_hex_color(color_value)
        if parsed is not None:
            return parsed
    return (1.0, 1.0, 1.0, 1.0)


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


def _srgb_to_linear_channel(value: float) -> float:
    clamped = min(1.0, max(0.0, float(value)))
    if clamped <= 0.04045:
        return clamped / 12.92
    return float(((clamped + 0.055) / 1.055) ** 2.4)


@dataclass(slots=True)
class _WgpuBackend:
    """Backend initialization scaffold used during migration."""

    surface: SurfaceHandle | None = None
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
    _frame_texture: object | None = field(init=False, default=None)
    _frame_texture_view: object | None = field(init=False, default=None)
    _command_encoder: object | None = field(init=False, default=None)
    _queued_packets: list[tuple[str, tuple[_DrawPacket, ...]]] = field(init=False, default_factory=list)
    _target_width: int = field(init=False, default=1200)
    _target_height: int = field(init=False, default=720)
    _upload_threshold_packets: int = field(init=False, default=256)
    _upload_mode_last: str = field(init=False, default="none")
    _uploaded_packet_count: int = field(init=False, default=0)
    _stream_write_cursor: int = field(init=False, default=0)
    _reconfigure_retry_limit: int = field(init=False, default=2)
    _reconfigure_attempts_last: int = field(init=False, default=0)
    _reconfigure_failures: int = field(init=False, default=0)
    _device_identity: int = field(init=False, default=0)
    _adapter_identity: int = field(init=False, default=0)
    _present_mode: str = field(init=False, default="fifo")
    _selected_backend: str = field(init=False, default="unknown")
    _adapter_info: dict[str, object] = field(init=False, default_factory=dict)
    _font_path: str = field(init=False, default="")
    _frame_in_flight: bool = field(init=False, default=False)
    _frame_in_flight_limit: int = field(init=False, default=1)

    def __post_init__(self) -> None:
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
        try:
            self._adapter, self._selected_backend = self._request_adapter()
            self._adapter_info = self._extract_adapter_info(self._adapter)
            self._device = self._request_device(self._adapter)
            self._font_path = _resolve_system_font_path()
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
        self._setup_pipelines()
        self._rebuild_frame_targets()
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
        self._queued_packets.clear()

    def draw_packets(self, pass_name: str, packets: tuple[_DrawPacket, ...]) -> None:
        self._queued_packets.append((str(pass_name), tuple(packets)))
        self._stage_draw_packets(packets)
        encoder = self._command_encoder
        if encoder is None:
            return
        begin_render_pass = getattr(encoder, "begin_render_pass", None)
        if not callable(begin_render_pass):
            return
        color_attachments = [
            {
                "view": self._frame_texture_view,
                "clear_value": (0.0, 0.0, 0.0, 1.0),
                "load_op": "clear",
                "store_op": "store",
            }
        ]
        render_pass = begin_render_pass(color_attachments=color_attachments)
        set_pipeline = getattr(render_pass, "set_pipeline", None)
        draw = getattr(render_pass, "draw", None)
        for packet in packets:
            pipeline = (
                self._text_pipeline
                if str(packet.kind) == "text"
                else self._geometry_pipeline
            )
            if callable(set_pipeline) and pipeline is not None:
                set_pipeline(pipeline)
            if callable(draw):
                draw(3, 1, 0, 0)
        end = getattr(render_pass, "end", None)
        if callable(end):
            end()

    def present(self) -> None:
        encoder = self._command_encoder
        if encoder is None:
            return
        finish = getattr(encoder, "finish", None)
        if not callable(finish):
            return
        command_buffer = finish()
        submit = getattr(self._queue, "submit", None)
        if callable(submit):
            submit([command_buffer])

    def end_frame(self) -> None:
        self._command_encoder = None
        self._frame_in_flight = False
        return

    def close(self) -> None:
        self._queued_packets.clear()
        self._frame_texture = None
        self._frame_texture_view = None
        self._command_encoder = None
        return

    def set_title(self, title: str) -> None:
        self._title = str(title)

    def reconfigure(self, event: WindowResizeEvent) -> None:
        self._target_width = max(1, int(event.physical_width))
        self._target_height = max(1, int(event.physical_height))
        self._surface_state["physical_width"] = self._target_width
        self._surface_state["physical_height"] = self._target_height
        self._surface_state["dpi_scale"] = float(event.dpi_scale)
        self._rebuild_frame_targets_with_retry()
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
            "surface_format": str(self._surface_format),
            "width": int(self._target_width),
            "height": int(self._target_height),
            "dpi_scale": dpi,
        }

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
        if callable(request_adapter_sync):
            for backend_name in backend_order:
                selected_backend = str(backend_name)
                try:
                    adapter = request_adapter_sync(
                        power_preference="high-performance",
                        backend=backend_name,
                    )
                except TypeError:
                    adapter = request_adapter_sync(power_preference="high-performance")
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
                    adapter = request_adapter(
                        power_preference="high-performance",
                        backend=backend_name,
                    )
                except TypeError:
                    adapter = request_adapter(power_preference="high-performance")
                if adapter is not None:
                    break
        if adapter is None:
            raise WgpuInitError(
                "wgpu adapter request returned None",
                details={
                    "selected_backend": selected_backend,
                    "attempted_backends": tuple(backend_order),
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
            "physical_width": self._target_width,
            "physical_height": self._target_height,
            "format": self._surface_format,
        }
        if self.surface is not None:
            state["surface_id"] = str(self.surface.surface_id)
            state["backend"] = str(self.surface.backend)
        state["present_mode"] = self._resolve_present_mode()
        self._present_mode = str(state["present_mode"])
        return state

    def _setup_pipelines(self) -> None:
        create_shader_module = getattr(self._device, "create_shader_module", None)
        create_render_pipeline = getattr(self._device, "create_render_pipeline", None)
        if not callable(create_shader_module) or not callable(create_render_pipeline):
            self._geometry_pipeline = {"kind": "geometry", "format": self._surface_format}
            self._text_pipeline = {"kind": "text", "format": self._surface_format}
            return
        geometry_shader = create_shader_module(code=_GEOMETRY_WGSL)
        text_shader = create_shader_module(code=_TEXT_WGSL)
        color_target = {"format": self._surface_format, "blend": None, "write_mask": 0xF}
        geometry_descriptor = {
            "layout": "auto",
            "vertex": {"module": geometry_shader, "entry_point": "vs_main", "buffers": []},
            "fragment": {
                "module": geometry_shader,
                "entry_point": "fs_main",
                "targets": [color_target],
            },
            "primitive": {"topology": "triangle-list"},
        }
        text_descriptor = {
            "layout": "auto",
            "vertex": {"module": text_shader, "entry_point": "vs_main", "buffers": []},
            "fragment": {
                "module": text_shader,
                "entry_point": "fs_main",
                "targets": [color_target],
            },
            "primitive": {"topology": "triangle-list"},
        }
        self._geometry_pipeline = create_render_pipeline(**geometry_descriptor)
        self._text_pipeline = create_render_pipeline(**text_descriptor)

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

    def _resolve_present_mode(self) -> str:
        raw_supported = os.getenv("ENGINE_WGPU_PRESENT_MODES", "").strip().lower()
        if raw_supported:
            supported = tuple(item.strip() for item in raw_supported.split(",") if item.strip())
        else:
            supported = ("fifo", "mailbox", "immediate")
        vsync_raw = os.getenv("ENGINE_RENDER_VSYNC", "1").strip().lower()
        vsync = vsync_raw in {"1", "true", "yes", "on"}
        if vsync:
            preferred = ("fifo", "mailbox", "immediate")
        else:
            preferred = ("mailbox", "immediate", "fifo")
        for mode in preferred:
            if mode in supported:
                return mode
        return "fifo"

    def _stage_draw_packets(self, packets: tuple[_DrawPacket, ...]) -> None:
        packet_count = int(len(packets))
        if packet_count <= 0:
            self._upload_mode_last = "none"
            self._uploaded_packet_count = 0
            return
        if packet_count <= self._upload_threshold_packets:
            self._upload_mode_last = "full_rewrite"
            self._uploaded_packet_count = packet_count
            self._upload_full_rewrite(packet_count)
            return
        self._upload_mode_last = "ring_buffer"
        self._uploaded_packet_count = packet_count
        self._upload_ring_buffer(packet_count)

    def _upload_full_rewrite(self, packet_count: int) -> None:
        create_buffer = getattr(self._device, "create_buffer", None)
        if not callable(create_buffer):
            return
        size = max(256, int(packet_count * 64))
        usage = _resolve_buffer_usage(self._wgpu)
        try:
            create_buffer(size=size, usage=usage, mapped_at_creation=False)
        except Exception:
            return

    def _upload_ring_buffer(self, packet_count: int) -> None:
        create_buffer = getattr(self._device, "create_buffer", None)
        if callable(create_buffer):
            size = max(1024, int(packet_count * 64))
            usage = _resolve_buffer_usage(self._wgpu)
            try:
                create_buffer(size=size, usage=usage, mapped_at_creation=False)
            except Exception:
                pass
        self._stream_write_cursor = (self._stream_write_cursor + packet_count) % 1_000_000


def _resolve_texture_usage(wgpu_mod: object) -> int:
    texture_usage = getattr(wgpu_mod, "TextureUsage", None)
    if texture_usage is None:
        return 0x10 | 0x04  # RENDER_ATTACHMENT | COPY_SRC (fallback)
    render_attachment = int(getattr(texture_usage, "RENDER_ATTACHMENT", 0x10))
    copy_src = int(getattr(texture_usage, "COPY_SRC", 0x04))
    return render_attachment | copy_src


def _resolve_buffer_usage(wgpu_mod: object) -> int:
    buffer_usage = getattr(wgpu_mod, "BufferUsage", None)
    if buffer_usage is None:
        return 0x80 | 0x20  # VERTEX | COPY_DST fallback
    vertex = int(getattr(buffer_usage, "VERTEX", 0x80))
    copy_dst = int(getattr(buffer_usage, "COPY_DST", 0x20))
    return vertex | copy_dst


def _resolve_backend_priority() -> tuple[str, ...]:
    raw = os.getenv("ENGINE_WGPU_BACKENDS", "").strip()
    if not raw:
        return ("vulkan", "metal", "dx12")
    values = tuple(
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    )
    return values or ("vulkan", "metal", "dx12")


def _resolve_system_font_path() -> str:
    checked: list[str] = []
    for candidate in _iter_system_font_candidates():
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


def _iter_system_font_candidates() -> tuple[str, ...]:
    candidates: list[str] = []
    env_value = os.getenv("ENGINE_WGPU_FONT_PATHS", "").strip()
    if env_value:
        for raw in env_value.split(os.pathsep):
            item = raw.strip()
            if item:
                candidates.append(item)
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
@vertex
fn vs_main(@builtin(vertex_index) vertex_index: u32) -> @builtin(position) vec4<f32> {
    var pos = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, -1.0),
        vec2<f32>( 3.0, -1.0),
        vec2<f32>(-1.0,  3.0),
    );
    return vec4<f32>(pos[vertex_index], 0.0, 1.0);
}

@fragment
fn fs_main() -> @location(0) vec4<f32> {
    return vec4<f32>(0.1, 0.1, 0.1, 1.0);
}
"""


_TEXT_WGSL = """
@vertex
fn vs_main(@builtin(vertex_index) vertex_index: u32) -> @builtin(position) vec4<f32> {
    var pos = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, -1.0),
        vec2<f32>( 3.0, -1.0),
        vec2<f32>(-1.0,  3.0),
    );
    return vec4<f32>(pos[vertex_index], 0.0, 1.0);
}

@fragment
fn fs_main() -> @location(0) vec4<f32> {
    return vec4<f32>(1.0, 1.0, 1.0, 1.0);
}
"""


__all__ = ["WgpuInitError", "WgpuRenderer"]

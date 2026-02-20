"""WGPU-backed renderer implementation scaffold."""

from __future__ import annotations

import os
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
    _diagnostics_hub: DiagnosticHub | None = field(init=False, default=None)
    _frame_index: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        factory = self._backend_factory or _create_wgpu_backend
        self._backend = factory(self.surface)

    def begin_frame(self) -> None:
        if self._closed or self._frame_active:
            return
        self._frame_active = True
        self._backend.begin_frame()
        self._emit_render_stage("begin_frame")

    def end_frame(self) -> None:
        if self._closed or not self._frame_active:
            return
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
        self._execute_immediate_command(command)

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
        self._execute_immediate_command(command)

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
        self._execute_immediate_command(command)

    def set_title(self, title: str) -> None:
        self._backend.set_title(title)

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        command = RenderCommand(
            kind="fill_window",
            layer=int(round(float(z) * 100.0)),
            data=(("key", str(key)), ("color", str(color)), ("z", float(z))),
        )
        self._execute_immediate_command(command)

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (float(x), float(y))

    def invalidate(self) -> None:
        return

    def run(self, draw_callback: Callable[[], None]) -> None:
        self._draw_callback = draw_callback
        if self._closed:
            return
        draw_callback()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._backend.close()

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        started_here = not self._frame_active
        if started_here:
            self.begin_frame()
        try:
            batches = self._build_pass_batches(snapshot)
            self._emit_render_stage(
                "build_batches",
                value={"pass_count": int(len(batches))},
            )
            self._execute_pass_batches(batches)
            self._emit_render_stage("execute_passes")
            self._backend.present()
            self._emit_render_stage("present")
        finally:
            if started_here:
                self.end_frame()

    def apply_window_resize(self, event: WindowResizeEvent) -> None:
        self.width = max(1, int(event.physical_width))
        self.height = max(1, int(event.physical_height))
        self._backend.reconfigure(event)

    def set_diagnostics_hub(self, hub: DiagnosticHub | None) -> None:
        self._diagnostics_hub = hub

    def _execute_immediate_command(self, command: RenderCommand) -> None:
        self._immediate_commands.append(command)
        if self._frame_active:
            return
        snapshot = RenderSnapshot(
            frame_index=self._frame_index,
            passes=(RenderPassSnapshot(name="overlay", commands=tuple(self._immediate_commands)),),
        )
        self._immediate_commands.clear()
        self.render_snapshot(snapshot)

    def _build_pass_batches(self, snapshot: RenderSnapshot) -> tuple[_RenderPassBatch, ...]:
        batches: list[_RenderPassBatch] = []
        for render_pass in snapshot.passes:
            descriptor = _resolve_pass_descriptor(render_pass.name)
            commands = tuple(
                sorted(
                    tuple(render_pass.commands),
                    key=lambda command: (
                        int(command.layer),
                        str(command.kind),
                        str(command.sort_key),
                    ),
                )
            )
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
    return _DrawPacket(
        kind=str(command.kind),
        layer=int(command.layer),
        sort_key=str(command.sort_key),
        transform=tuple(float(value) for value in command.transform.values),
        data=tuple((str(key), value) for key, value in command.data),
    )


def _create_wgpu_backend(surface: SurfaceHandle | None) -> _Backend:
    return _WgpuBackend(surface=surface)


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

    def __post_init__(self) -> None:
        try:
            import wgpu
        except Exception as exc:
            raise RuntimeError(f"wgpu dependency unavailable: {exc!r}") from exc
        self._wgpu = wgpu
        self._adapter = self._request_adapter()
        self._device = self._request_device(self._adapter)
        self._queue = getattr(self._device, "queue", None)
        if self._queue is None:
            raise RuntimeError("wgpu device queue unavailable")
        self._surface_state = self._setup_surface_state()
        self._setup_pipelines()
        self._rebuild_frame_targets()
        self._wgpu_loaded = True

    def begin_frame(self) -> None:
        create_command_encoder = getattr(self._device, "create_command_encoder", None)
        if callable(create_command_encoder):
            self._command_encoder = create_command_encoder(label="engine.wgpu.frame")
        else:
            self._command_encoder = SimpleNamespace()
        self._queued_packets.clear()

    def draw_packets(self, pass_name: str, packets: tuple[_DrawPacket, ...]) -> None:
        self._queued_packets.append((str(pass_name), tuple(packets)))
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
        self._rebuild_frame_targets()
        return

    def _request_adapter(self) -> object:
        gpu = getattr(self._wgpu, "gpu", None)
        if gpu is None:
            raise RuntimeError("wgpu.gpu entrypoint unavailable")
        backend_order = _resolve_backend_priority()
        request_adapter_sync = getattr(gpu, "request_adapter_sync", None)
        adapter = None
        if callable(request_adapter_sync):
            for backend_name in backend_order:
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
                raise RuntimeError("wgpu adapter request API unavailable")
            for backend_name in backend_order:
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
            raise RuntimeError("wgpu adapter request returned None")
        return adapter

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
            raise RuntimeError("wgpu device request returned None")
        return device

    def _setup_surface_state(self) -> dict[str, object]:
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


def _resolve_texture_usage(wgpu_mod: object) -> int:
    texture_usage = getattr(wgpu_mod, "TextureUsage", None)
    if texture_usage is None:
        return 0x10 | 0x04  # RENDER_ATTACHMENT | COPY_SRC (fallback)
    render_attachment = int(getattr(texture_usage, "RENDER_ATTACHMENT", 0x10))
    copy_src = int(getattr(texture_usage, "COPY_SRC", 0x04))
    return render_attachment | copy_src


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


__all__ = ["WgpuRenderer"]

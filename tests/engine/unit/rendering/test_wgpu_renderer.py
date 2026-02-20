from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace

from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.api.window import WindowResizeEvent
from engine.rendering.wgpu_renderer import _WgpuBackend, WgpuRenderer


@dataclass(slots=True)
class _FakeBackend:
    begin_calls: int = 0
    present_calls: int = 0
    end_calls: int = 0
    close_calls: int = 0
    title: str = ""
    resize_events: list[WindowResizeEvent] = field(default_factory=list)
    passes: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    def begin_frame(self) -> None:
        self.begin_calls += 1

    def draw_packets(self, pass_name: str, packets) -> None:
        kinds = tuple(str(packet.kind) for packet in packets)
        self.passes.append((str(pass_name), kinds))

    def present(self) -> None:
        self.present_calls += 1

    def end_frame(self) -> None:
        self.end_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def set_title(self, title: str) -> None:
        self.title = str(title)

    def reconfigure(self, event: WindowResizeEvent) -> None:
        self.resize_events.append(event)

    def resize_telemetry(self) -> dict[str, object]:
        return {
            "renderer_reused": True,
            "device_reused": True,
            "adapter_reused": True,
            "reconfigure_attempts": 1,
            "reconfigure_failures": 0,
            "present_mode": "fifo",
            "surface_format": "bgra8unorm-srgb",
            "width": 1600,
            "height": 1200,
            "dpi_scale": 2.0,
        }


@dataclass(slots=True)
class _FakeHub:
    events: list[str] = field(default_factory=list)

    def emit_fast(self, *, category: str, name: str, **kwargs) -> None:
        _ = kwargs
        if category == "render":
            self.events.append(name)


def test_wgpu_renderer_renders_empty_snapshot() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)

    renderer.render_snapshot(RenderSnapshot(frame_index=1, passes=()))

    assert backend.begin_calls == 1
    assert backend.present_calls == 1
    assert backend.end_calls == 1
    assert backend.passes == []


def test_wgpu_renderer_renders_simple_rect_grid_text_snapshot() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    snapshot = RenderSnapshot(
        frame_index=3,
        passes=(
            RenderPassSnapshot(
                name="overlay",
                commands=(
                    RenderCommand(kind="text", layer=20, sort_key="b"),
                    RenderCommand(kind="grid", layer=10, sort_key="a"),
                    RenderCommand(kind="rect", layer=10, sort_key="b"),
                ),
            ),
        ),
    )

    renderer.render_snapshot(snapshot)

    assert backend.passes == [("overlay", ("grid", "rect", "text"))]


def test_wgpu_renderer_pass_execution_order_is_deterministic() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    snapshot = RenderSnapshot(
        frame_index=5,
        passes=(
            RenderPassSnapshot(name="ui", commands=(RenderCommand(kind="text"),)),
            RenderPassSnapshot(name="world", commands=(RenderCommand(kind="rect"),)),
            RenderPassSnapshot(name="post_bloom", commands=(RenderCommand(kind="grid"),)),
        ),
    )

    renderer.render_snapshot(snapshot)

    assert [name for name, _ in backend.passes] == ["world", "overlay", "post_bloom"]


def test_wgpu_renderer_immediate_mode_uses_common_batch_stage() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)

    renderer.add_rect("k", 1.0, 2.0, 3.0, 4.0, "#fff")
    renderer.add_grid("g", 1.0, 2.0, 3.0, 4.0, 4, "#ccc")
    renderer.add_text("t", "X", 1.0, 2.0)

    assert backend.begin_calls == 3
    assert backend.present_calls == 3
    assert backend.end_calls == 3
    assert backend.passes == [
        ("overlay", ("rect",)),
        ("overlay", ("rect", "grid")),
        ("overlay", ("rect", "grid", "text")),
    ]


def test_wgpu_renderer_merges_immediate_commands_during_active_frame() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)

    renderer.begin_frame()
    renderer.add_rect("a", 0.0, 0.0, 1.0, 1.0, "#fff")
    renderer.add_text("b", "T", 0.0, 0.0)
    renderer.end_frame()

    assert backend.begin_calls == 1
    assert backend.present_calls == 1
    assert backend.end_calls == 1
    assert backend.passes == [("overlay", ("rect", "text"))]


def test_wgpu_renderer_emits_explicit_render_stage_diagnostics() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    hub = _FakeHub()
    renderer.set_diagnostics_hub(hub)  # type: ignore[arg-type]

    renderer.render_snapshot(
        RenderSnapshot(
            frame_index=7,
            passes=(RenderPassSnapshot(name="overlay", commands=(RenderCommand(kind="rect"),)),),
        )
    )

    assert "render.stage.begin_frame" in hub.events
    assert "render.stage.build_batches" in hub.events
    assert "render.stage.execute_pass.begin" in hub.events
    assert "render.stage.execute_pass.end" in hub.events
    assert "render.stage.execute_passes" in hub.events
    assert "render.stage.present" in hub.events
    assert "render.stage.end_frame" in hub.events


def test_wgpu_renderer_can_forward_resize_and_title() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    event = WindowResizeEvent(
        logical_width=800.0,
        logical_height=600.0,
        physical_width=1600,
        physical_height=1200,
        dpi_scale=2.0,
    )

    renderer.set_title("phase3")
    renderer.apply_window_resize(event)
    renderer.close()

    assert backend.title == "phase3"
    assert backend.resize_events == [event]
    assert backend.close_calls == 1


def test_wgpu_renderer_emits_resize_diagnostics_with_dpi_and_dims() -> None:
    backend = _FakeBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    hub = _FakeHub()
    renderer.set_diagnostics_hub(hub)  # type: ignore[arg-type]
    event = WindowResizeEvent(
        logical_width=800.0,
        logical_height=600.0,
        physical_width=1600,
        physical_height=1200,
        dpi_scale=2.0,
    )

    renderer.apply_window_resize(event)

    assert "render.resize_event" in hub.events
    assert "render.viewport_applied" in hub.events
    assert "render.surface_reconfigure" in hub.events


class _FakeEncoder:
    def __init__(self) -> None:
        self.render_passes: list[_FakeRenderPass] = []

    def begin_render_pass(self, **kwargs):
        _ = kwargs
        render_pass = _FakeRenderPass()
        self.render_passes.append(render_pass)
        return render_pass

    def finish(self):
        return "cmd"


class _FakeRenderPass:
    def __init__(self) -> None:
        self.pipelines: list[object] = []
        self.draw_calls: int = 0
        self.ended: bool = False

    def set_pipeline(self, pipeline: object) -> None:
        self.pipelines.append(pipeline)

    def draw(self, *_args) -> None:
        self.draw_calls += 1

    def end(self) -> None:
        self.ended = True


class _FakeQueue:
    def __init__(self) -> None:
        self.submissions: list[list[object]] = []

    def submit(self, cmds: list[object]) -> None:
        self.submissions.append(cmds)


class _FakeTexture:
    def create_view(self) -> object:
        return object()


class _FakeDevice:
    def __init__(self) -> None:
        self.queue = _FakeQueue()
        self.encoders: list[_FakeEncoder] = []
        self.shader_modules: list[str] = []
        self.pipelines: list[dict[str, object]] = []
        self.textures: list[tuple[object, ...]] = []
        self.buffers: list[tuple[object, ...]] = []

    def create_command_encoder(self, label: str = "") -> _FakeEncoder:
        _ = label
        encoder = _FakeEncoder()
        self.encoders.append(encoder)
        return encoder

    def create_shader_module(self, *, code: str) -> object:
        self.shader_modules.append(code)
        return {"code": code}

    def create_render_pipeline(self, **descriptor):
        self.pipelines.append(descriptor)
        return descriptor

    def create_texture(self, **kwargs):
        size = kwargs.get("size")
        if isinstance(size, tuple) and len(size) >= 2:
            if int(size[0]) <= 0 or int(size[1]) <= 0:
                raise RuntimeError("invalid texture size")
        self.textures.append(tuple(kwargs.items()))
        return _FakeTexture()

    def create_buffer(self, **kwargs):
        self.buffers.append(tuple(kwargs.items()))
        return object()


class _FakeAdapter:
    def __init__(self, device: _FakeDevice) -> None:
        self._device = device

    def request_device_sync(self, **kwargs):
        _ = kwargs
        return self._device


def _install_fake_wgpu_module(monkeypatch) -> _FakeDevice:
    device = _FakeDevice()
    adapter = _FakeAdapter(device)
    gpu = SimpleNamespace(request_adapter_sync=lambda **kwargs: adapter)
    texture_usage = SimpleNamespace(RENDER_ATTACHMENT=0x10, COPY_SRC=0x04)
    buffer_usage = SimpleNamespace(VERTEX=0x80, COPY_DST=0x20)
    fake_mod = ModuleType("wgpu")
    fake_mod.gpu = gpu
    fake_mod.TextureUsage = texture_usage
    fake_mod.BufferUsage = buffer_usage
    monkeypatch.setitem(sys.modules, "wgpu", fake_mod)
    return device


def test_wgpu_backend_sets_up_device_surface_pipelines_and_pass_encoding(monkeypatch) -> None:
    device = _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()

    assert backend._wgpu_loaded is True  # noqa: SLF001
    assert backend._device is device  # noqa: SLF001
    assert backend._geometry_pipeline is not None  # noqa: SLF001
    assert backend._text_pipeline is not None  # noqa: SLF001

    backend.begin_frame()
    backend.draw_packets(
        "overlay",
        (
            SimpleNamespace(kind="rect"),
            SimpleNamespace(kind="text"),
        ),
    )
    backend.present()
    backend.end_frame()

    assert device.encoders
    assert device.queue.submissions == [["cmd"]]


def test_wgpu_backend_uses_hybrid_upload_modes(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    backend._upload_threshold_packets = 2  # noqa: SLF001

    backend.begin_frame()
    backend.draw_packets(
        "overlay",
        (
            SimpleNamespace(kind="rect"),
            SimpleNamespace(kind="grid"),
        ),
    )
    assert backend._upload_mode_last == "full_rewrite"  # noqa: SLF001

    backend.draw_packets(
        "overlay",
        (
            SimpleNamespace(kind="rect"),
            SimpleNamespace(kind="grid"),
            SimpleNamespace(kind="text"),
        ),
    )
    assert backend._upload_mode_last == "ring_buffer"  # noqa: SLF001


def test_wgpu_backend_resize_reconfigure_reuses_device_and_retries(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    baseline_device_id = id(backend._device)  # noqa: SLF001
    event = WindowResizeEvent(
        logical_width=640.0,
        logical_height=480.0,
        physical_width=1280,
        physical_height=960,
        dpi_scale=2.0,
    )

    backend.reconfigure(event)
    telemetry = backend.resize_telemetry()

    assert id(backend._device) == baseline_device_id  # noqa: SLF001
    assert telemetry["device_reused"] is True
    assert int(telemetry["reconfigure_attempts"]) >= 1
    assert int(telemetry["reconfigure_failures"]) >= 0
    assert float(telemetry["dpi_scale"]) == 2.0


def test_wgpu_backend_present_mode_fallback_chain(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    monkeypatch.setenv("ENGINE_RENDER_VSYNC", "0")
    monkeypatch.setenv("ENGINE_WGPU_PRESENT_MODES", "fifo,immediate")
    backend = _WgpuBackend()

    assert backend._present_mode == "immediate"  # noqa: SLF001

from __future__ import annotations

import builtins
import sys
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace

import pytest

from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.api.window import WindowResizeEvent
import engine.rendering.wgpu_renderer as wgpu_renderer
from engine.rendering.wgpu_renderer import _WgpuBackend, WgpuInitError, WgpuRenderer


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


def test_wgpu_renderer_command_sort_uses_deterministic_tie_break_keys() -> None:
    @dataclass(slots=True)
    class _OrderBackend(_FakeBackend):
        sort_keys: list[tuple[str, ...]] = field(default_factory=list)

        def draw_packets(self, pass_name: str, packets) -> None:
            super().draw_packets(pass_name, packets)
            self.sort_keys.append(tuple(str(packet.data[0][1]) for packet in packets))

    backend = _OrderBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    snapshot = RenderSnapshot(
        frame_index=9,
        passes=(
            RenderPassSnapshot(
                name="overlay",
                commands=(
                    RenderCommand(kind="rect", layer=10, sort_key="a", data=(("key", "b"),)),
                    RenderCommand(kind="rect", layer=10, sort_key="a", data=(("key", "a"),)),
                    RenderCommand(kind="rect", layer=10, sort_key="a", data=(("key", "c"),)),
                ),
            ),
        ),
    )

    renderer.render_snapshot(snapshot)

    assert backend.passes == [("overlay", ("rect", "rect", "rect"))]
    assert backend.sort_keys == [("a", "b", "c")]


def test_wgpu_renderer_normalized_golden_subset_for_packet_translation() -> None:
    @dataclass(slots=True)
    class _GoldenBackend(_FakeBackend):
        normalized_packets: list[tuple[str, tuple[tuple[object, ...], ...]]] = field(default_factory=list)

        def draw_packets(self, pass_name: str, packets) -> None:
            super().draw_packets(pass_name, packets)
            normalized: list[tuple[object, ...]] = []
            for packet in packets:
                payload = dict(packet.data)
                linear_rgba = tuple(round(float(v), 6) for v in payload.get("linear_rgba", ()))
                normalized.append(
                    (
                        str(packet.kind),
                        int(packet.layer),
                        str(packet.sort_key),
                        str(payload.get("key", "")),
                        str(payload.get("color", "")),
                        linear_rgba,
                    )
                )
            self.normalized_packets.append((str(pass_name), tuple(normalized)))

    backend = _GoldenBackend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    snapshot = RenderSnapshot(
        frame_index=11,
        passes=(
            RenderPassSnapshot(
                name="overlay",
                commands=(
                    RenderCommand(kind="text", layer=2, sort_key="b", data=(("key", "title"), ("color", "#ffffff"))),
                    RenderCommand(kind="rect", layer=1, sort_key="a", data=(("key", "panel"), ("color", "#808080"))),
                ),
            ),
            RenderPassSnapshot(
                name="world",
                commands=(
                    RenderCommand(kind="grid", layer=0, sort_key="g", data=(("key", "board"), ("color", "#00ff00"))),
                ),
            ),
        ),
    )

    renderer.render_snapshot(snapshot)

    assert backend.normalized_packets == [
        (
            "world",
            (
                ("grid", 0, "g", "board", "#00ff00", (0.0, 1.0, 0.0, 1.0)),
            ),
        ),
        (
            "overlay",
            (
                ("rect", 1, "a", "panel", "#808080", (0.215861, 0.215861, 0.215861, 1.0)),
                ("text", 2, "b", "title", "#ffffff", (1.0, 1.0, 1.0, 1.0)),
            ),
        ),
    ]


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


def test_grid_draw_rects_span_declared_bounds_without_extra_division() -> None:
    rects = wgpu_renderer._grid_draw_rects(
        {"x": 10.0, "y": 20.0, "width": 100.0, "height": 80.0, "lines": 11},
        color=(1.0, 1.0, 1.0, 1.0),
    )

    assert len(rects) == 22
    for rect in rects:
        assert rect.x >= 10.0
        assert rect.y >= 20.0
        assert rect.x + rect.w <= 110.0001
        assert rect.y + rect.h <= 100.0001


def test_text_draw_rects_generates_readable_glyph_quads() -> None:
    rects = wgpu_renderer._text_draw_rects(
        {"text": "Menu", "x": 100.0, "y": 50.0, "font_size": 16.0, "anchor": "middle-center"},
        color=(1.0, 1.0, 1.0, 1.0),
    )

    assert rects
    min_x = min(rect.x for rect in rects)
    max_x = max(rect.x + rect.w for rect in rects)
    min_y = min(rect.y for rect in rects)
    max_y = max(rect.y + rect.h for rect in rects)
    assert min_x < 100.0 < max_x
    assert min_y < 50.0 < max_y


def test_text_draw_rects_merges_pixel_runs_for_fewer_quads() -> None:
    rects = wgpu_renderer._text_draw_rects(
        {"text": "W", "x": 0.0, "y": 0.0, "font_size": 24.0, "anchor": "top-left"},
        color=(1.0, 1.0, 1.0, 1.0),
    )

    assert 0 < len(rects) < 35
    assert all(rect.w >= 3.0 for rect in rects)


def test_system_font_candidates_env_is_explicit_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENGINE_WGPU_FONT_PATHS", "X:\\missing1.ttf;X:\\missing2.ttf")

    candidates = wgpu_renderer._iter_system_font_candidates()

    assert candidates == ("X:\\missing1.ttf", "X:\\missing2.ttf")


def test_wgpu_backend_batches_many_rects_into_one_render_pass(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    backend.begin_frame()
    packets = tuple(SimpleNamespace(kind="rect") for _ in range(16))

    backend.draw_packets("overlay", packets)

    encoder = backend._command_encoder  # noqa: SLF001
    assert encoder is not None
    assert len(encoder.render_passes) == 1
    backend.end_frame()


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


class _FlakyQueue(_FakeQueue):
    def __init__(self, fail_times: int = 1) -> None:
        super().__init__()
        self._fail_times = fail_times

    def submit(self, cmds: list[object]) -> None:
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("submit failed")
        super().submit(cmds)


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


def test_wgpu_backend_present_mode_vsync_on_fallback_chain(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    monkeypatch.setenv("ENGINE_RENDER_VSYNC", "1")
    monkeypatch.setenv("ENGINE_WGPU_PRESENT_MODES", "immediate")
    backend = _WgpuBackend()

    assert backend._present_mode == "immediate"  # noqa: SLF001
    telemetry = backend.resize_telemetry()
    assert telemetry["vsync_enabled"] is True
    assert telemetry["present_mode_supported"] == ("immediate",)


def test_wgpu_backend_color_policy_uses_srgb_surface_and_linear_payload(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    command = RenderCommand(
        kind="rect",
        layer=1,
        sort_key="k",
        data=(("color", "#808080"),),
    )

    packet = wgpu_renderer._command_to_packet(command)  # noqa: SLF001
    payload = dict(packet.data)
    linear = payload["linear_rgba"]
    srgb = payload["srgb_rgba"]

    assert "srgb" in backend._surface_format  # noqa: SLF001
    assert isinstance(srgb, tuple)
    assert isinstance(linear, tuple)
    assert float(srgb[0]) > float(linear[0])
    assert float(linear[0]) == pytest.approx(0.21586, rel=1e-3)


def test_wgpu_backend_rejects_non_srgb_surface_format(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    backend._surface_format = "bgra8unorm"  # noqa: SLF001

    with pytest.raises(RuntimeError, match="must be sRGB"):
        backend._setup_surface_state()  # noqa: SLF001


def test_wgpu_backend_one_frame_in_flight_baseline(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()

    backend.begin_frame()
    with pytest.raises(RuntimeError, match="one frame in flight"):
        backend.begin_frame()
    backend.end_frame()


def test_wgpu_backend_runtime_render_path_performs_no_asset_io(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    command = RenderCommand(
        kind="rect",
        data=(("color", "#abcdef"),),
    )
    packet = wgpu_renderer._command_to_packet(command)  # noqa: SLF001

    def _fail_open(*args, **kwargs):
        _ = (args, kwargs)
        raise AssertionError("runtime render path must not perform asset I/O")

    def _fail_scandir(*args, **kwargs):
        _ = (args, kwargs)
        raise AssertionError("runtime render path must not scan asset directories")

    monkeypatch.setattr(builtins, "open", _fail_open)
    monkeypatch.setattr(wgpu_renderer.os, "scandir", _fail_scandir)

    backend.begin_frame()
    backend.draw_packets("overlay", (packet,))
    backend.present()
    backend.end_frame()


def test_wgpu_backend_uses_system_font_fallback(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    monkeypatch.setattr(
        wgpu_renderer,
        "_resolve_system_font_path",
        lambda: r"C:\Windows\Fonts\arial.ttf",
    )
    backend = _WgpuBackend()

    assert backend._font_path.endswith("arial.ttf")  # noqa: SLF001


def test_wgpu_backend_fails_when_system_font_discovery_fails(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)

    def _raise_font_error() -> str:
        raise WgpuInitError(
            "system font discovery failed",
            details={
                "selected_backend": "unknown",
                "adapter_info": {},
                "font_candidates_checked": (),
            },
        )

    monkeypatch.setattr(wgpu_renderer, "_resolve_system_font_path", _raise_font_error)

    with pytest.raises(WgpuInitError, match="wgpu backend initialization failed") as exc_info:
        _WgpuBackend()
    assert "font_candidates_checked" in exc_info.value.details


def test_wgpu_backend_acquire_frame_view_recovers_after_one_failure(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()

    class _FlakyContext:
        def __init__(self) -> None:
            self.failures_left = 1

        def get_current_texture(self):
            if self.failures_left > 0:
                self.failures_left -= 1
                raise RuntimeError("acquire failed")
            return _FakeTexture()

        def configure(self, **kwargs) -> None:
            _ = kwargs

    backend._canvas_context = _FlakyContext()  # noqa: SLF001
    view = backend._acquire_frame_color_view()  # noqa: SLF001

    assert view is not None
    telemetry = backend.resize_telemetry()
    assert int(telemetry["acquire_failures"]) >= 1
    assert int(telemetry["acquire_recoveries"]) >= 1


def test_wgpu_backend_present_recovers_after_submit_failure(monkeypatch) -> None:
    _install_fake_wgpu_module(monkeypatch)
    backend = _WgpuBackend()
    backend._queue = _FlakyQueue(fail_times=1)  # noqa: SLF001
    backend._command_encoder = _FakeEncoder()  # noqa: SLF001

    backend.present()

    telemetry = backend.resize_telemetry()
    assert int(telemetry["present_failures"]) >= 1
    assert int(telemetry["present_recoveries"]) >= 1

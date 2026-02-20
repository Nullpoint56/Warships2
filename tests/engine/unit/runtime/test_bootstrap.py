from __future__ import annotations

import pytest

import engine.runtime.bootstrap as bootstrap
from engine.api.window import SurfaceHandle
from engine.runtime.host import EngineHostConfig


class FakeRenderer:
    def __init__(self, surface=None) -> None:
        self.surface = surface
        self.invalidated = 0

    def invalidate(self) -> None:
        self.invalidated += 1


class FakeInputController:
    def __init__(self, on_click_queued) -> None:
        self.on_click_queued = on_click_queued
        self.bound_canvas = None

    def bind(self, canvas) -> None:
        self.bound_canvas = canvas


class FakeWindow:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def show_fullscreen(self) -> None:
        self.calls.append(("show_fullscreen", ()))

    def show_maximized(self) -> None:
        self.calls.append(("show_maximized", ()))

    def show_windowed(self, width: int, height: int) -> None:
        self.calls.append(("show_windowed", (width, height)))

    def sync_ui(self) -> None:
        self.calls.append(("sync_ui", ()))

    def run(self) -> None:
        self.calls.append(("run", ()))


class FakeWindowLayer:
    def __init__(self, canvas) -> None:
        self.canvas = canvas

    def create_surface(self) -> SurfaceHandle:
        return SurfaceHandle(surface_id="main", backend="rendercanvas.glfw", provider=self.canvas)


class FakeHost:
    last_instance = None

    def __init__(self, module, config, render_api=None) -> None:
        self.module = module
        self.config = config
        self.render_api = render_api
        FakeHost.last_instance = self


def test_bootstrap_uses_window_mode_and_wires_runtime(monkeypatch) -> None:
    fake_window = FakeWindow()

    def fake_create_window(*, renderer, window, input_controller, host):
        assert isinstance(renderer, FakeRenderer)
        assert isinstance(window, FakeWindowLayer)
        assert isinstance(input_controller, FakeInputController)
        assert isinstance(host, FakeHost)
        return fake_window

    monkeypatch.setattr(bootstrap, "WgpuRenderer", FakeRenderer)
    monkeypatch.setattr(
        bootstrap,
        "create_rendercanvas_window",
        lambda **kwargs: FakeWindowLayer(canvas=object()),
    )
    monkeypatch.setattr(bootstrap, "InputController", FakeInputController)
    monkeypatch.setattr(bootstrap, "EngineHost", FakeHost)
    monkeypatch.setattr(bootstrap, "create_window_frontend", fake_create_window)

    marker = object()
    config = EngineHostConfig(window_mode="maximized", width=1280, height=720)
    bootstrap.run_hosted_runtime(
        module_factory=lambda renderer, layout: marker, host_config=config
    )

    assert FakeHost.last_instance is not None
    assert FakeHost.last_instance.module is marker
    assert fake_window.calls[0] == ("show_maximized", ())
    assert fake_window.calls[1] == ("sync_ui", ())
    assert fake_window.calls[2] == ("run", ())


def test_bootstrap_non_headless_raises_hard_error_when_wgpu_init_fails(monkeypatch) -> None:
    monkeypatch.delenv("ENGINE_HEADLESS", raising=False)
    monkeypatch.setattr(
        bootstrap,
        "create_rendercanvas_window",
        lambda **kwargs: FakeWindowLayer(canvas=object()),
    )

    def _raise_renderer_init(*, surface):
        _ = surface
        raise RuntimeError("wgpu init fail")

    monkeypatch.setattr(bootstrap, "WgpuRenderer", _raise_renderer_init)

    with pytest.raises(RuntimeError, match="wgpu_init_failed"):
        bootstrap.run_hosted_runtime(module_factory=lambda renderer, layout: object())


def test_bootstrap_non_headless_failure_details_include_phase4_fields(monkeypatch) -> None:
    monkeypatch.delenv("ENGINE_HEADLESS", raising=False)
    monkeypatch.setattr(
        bootstrap,
        "create_rendercanvas_window",
        lambda **kwargs: FakeWindowLayer(canvas=object()),
    )

    class _InitFailure(bootstrap.WgpuInitError):
        pass

    def _raise_renderer_init(*, surface):
        _ = surface
        raise _InitFailure(
            "backend init failed",
            details={"selected_backend": "vulkan", "adapter_info": {"vendor": "stub"}},
        )

    monkeypatch.setattr(bootstrap, "WgpuRenderer", _raise_renderer_init)

    with pytest.raises(RuntimeError, match="wgpu_init_failed details=") as exc_info:
        bootstrap.run_hosted_runtime(module_factory=lambda renderer, layout: object())

    message = str(exc_info.value)
    assert "'selected_backend': 'vulkan'" in message
    assert "'adapter_info': {'vendor': 'stub'}" in message
    assert "'attempted_surface_format': 'bgra8unorm-srgb'" in message
    assert "'platform':" in message
    assert "'stack':" in message


def test_bootstrap_headless_skips_window_and_renderer(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_HEADLESS", "1")
    calls: list[str] = []

    class _HeadlessModule:
        def on_start(self, host) -> None:
            _ = host

        def on_input_snapshot(self, snapshot) -> bool:
            _ = snapshot
            return False

        def simulate(self, context) -> None:
            _ = context
            calls.append("simulate")

        def build_render_snapshot(self):
            return None

        def should_close(self) -> bool:
            return len(calls) >= 1

        def on_shutdown(self) -> None:
            calls.append("shutdown")

    bootstrap.run_hosted_runtime(module_factory=lambda renderer, layout: _HeadlessModule())
    assert calls == ["simulate", "shutdown"]


def test_bootstrap_headless_and_backend_priority_parsing(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_HEADLESS", "true")
    monkeypatch.setenv("ENGINE_WGPU_BACKENDS", "vulkan,metal,dx12")

    assert bootstrap._resolve_engine_headless() is True  # noqa: SLF001
    assert bootstrap._resolve_wgpu_backend_priority() == ("vulkan", "metal", "dx12")  # noqa: SLF001

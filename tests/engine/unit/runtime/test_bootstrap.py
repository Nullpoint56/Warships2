from __future__ import annotations

import engine.runtime.bootstrap as bootstrap
from engine.runtime.host import EngineHostConfig


class FakeRenderer:
    def __init__(self, canvas=None) -> None:
        self.canvas = object() if canvas is None else canvas
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

    monkeypatch.setattr(bootstrap, "SceneRenderer", FakeRenderer)
    monkeypatch.setattr(
        bootstrap,
        "create_rendercanvas_window",
        lambda **kwargs: FakeWindowLayer(canvas=object()),
    )
    monkeypatch.setattr(bootstrap, "InputController", FakeInputController)
    monkeypatch.setattr(bootstrap, "EngineHost", FakeHost)
    monkeypatch.setattr(bootstrap, "create_pygfx_window", fake_create_window)

    marker = object()
    config = EngineHostConfig(window_mode="maximized", width=1280, height=720)
    bootstrap.run_pygfx_hosted_runtime(
        module_factory=lambda renderer, layout: marker, host_config=config
    )

    assert FakeHost.last_instance is not None
    assert FakeHost.last_instance.module is marker
    assert fake_window.calls[0] == ("show_maximized", ())
    assert fake_window.calls[1] == ("sync_ui", ())
    assert fake_window.calls[2] == ("run", ())

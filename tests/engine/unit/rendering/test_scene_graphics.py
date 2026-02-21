from __future__ import annotations

import engine.rendering as rendering_pkg
from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.rendering.wgpu_renderer import WgpuRenderer


def test_rendering_package_exports_backend_neutral_renderer_only() -> None:
    assert "WgpuRenderer" in rendering_pkg.__all__
    assert "SceneRenderer" not in rendering_pkg.__all__


def test_backend_agnostic_render_snapshot_contract_on_wgpu_renderer() -> None:
    class _Backend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def begin_frame(self) -> None:
            self.calls.append(("stage", "begin_frame"))

        def draw_packets(self, pass_name: str, packets) -> None:
            _ = packets
            self.calls.append(("pass", str(pass_name)))

        def present(self) -> None:
            self.calls.append(("stage", "present"))

        def end_frame(self) -> None:
            self.calls.append(("stage", "end_frame"))

        def close(self) -> None:
            return

        def set_title(self, title: str) -> None:
            _ = title
            return

        def reconfigure(self, event) -> None:
            _ = event
            return

        def resize_telemetry(self) -> dict[str, object]:
            return {}

    backend = _Backend()
    renderer = WgpuRenderer(_backend_factory=lambda _surface: backend)
    snapshot = RenderSnapshot(
        frame_index=1,
        passes=(RenderPassSnapshot(name="overlay", commands=(RenderCommand(kind="rect"),)),),
    )

    renderer.render_snapshot(snapshot)

    assert ("pass", "overlay") in backend.calls
    assert ("stage", "present") in backend.calls

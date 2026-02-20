from __future__ import annotations

from engine.api.render_snapshot import RenderSnapshot
from engine.runtime.host import EngineHost, EngineHostConfig


class _Module:
    def __init__(self) -> None:
        self.started = False
        self.shutdown = False

    def on_start(self, host) -> None:
        _ = host
        self.started = True

    def on_input_snapshot(self, snapshot) -> bool:
        _ = snapshot
        return False

    def simulate(self, context) -> None:
        _ = context

    def build_render_snapshot(self) -> RenderSnapshot:
        return RenderSnapshot(frame_index=0, passes=())

    def should_close(self) -> bool:
        return True

    def on_shutdown(self) -> None:
        self.shutdown = True


class _Renderer:
    def __init__(self) -> None:
        self.submitted = 0

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        _ = snapshot
        self.submitted += 1


def test_diagnostics_disabled_still_runs_host_frame_flow() -> None:
    module = _Module()
    renderer = _Renderer()
    host = EngineHost(module=module, config=EngineHostConfig(), render_api=renderer)

    host.frame()

    assert module.started is True
    assert module.shutdown is True
    assert renderer.submitted == 1

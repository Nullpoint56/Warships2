"""Engine runtime window frontend."""

from __future__ import annotations

from engine.api.debug import DiagnosticsEventEmitter
from engine.api.input_snapshot import InputSnapshot
from engine.api.render import RenderAPI
from engine.api.window import (
    WindowCloseEvent,
    WindowFocusEvent,
    WindowMinimizeEvent,
    WindowPort,
    WindowResizeEvent,
)
from engine.input.input_controller import InputController
from engine.runtime.host import EngineHost


class HostedWindowFrontend:
    """Frontend adapter over window/event loop and renderer APIs."""

    def __init__(
        self,
        renderer: RenderAPI,
        window: WindowPort,
        input_controller: InputController,
        host: EngineHost,
    ) -> None:
        self._renderer = renderer
        self._window = window
        self._input = input_controller
        self._host = host

    def show_fullscreen(self) -> None:
        self._window.set_fullscreen()

    def show_maximized(self) -> None:
        self._window.set_maximized()

    def show_windowed(self, width: int, height: int) -> None:
        self._window.set_windowed(width, height)

    def sync_ui(self) -> None:
        self._renderer.invalidate()

    def run(self) -> None:
        self._renderer.run(self._draw_frame)
        self._window.set_draw_handler(self._draw_frame)
        self._window.request_draw()
        self._window.run_loop()

    def _draw_frame(self) -> None:
        self._process_window_events()
        snapshot = self._build_input_snapshot()
        self._dispatch_input_snapshot(snapshot)
        self._host.frame()
        if self._host.is_closed():
            self._renderer.close()
            self._window.close()

    def _process_window_events(self) -> None:
        events = self._window.poll_events()
        if not events:
            return
        hub: DiagnosticsEventEmitter = self._host.diagnostics_hub
        tick = int(self._host.current_frame_index())
        resize_events_seen = 0
        for event in events:
            if isinstance(event, WindowResizeEvent):
                resize_events_seen += 1
                self._renderer.apply_window_resize(event)
                hub.emit_fast(
                    category="window",
                    name="window.resize",
                    tick=tick,
                    value={
                        "logical_width": float(event.logical_width),
                        "logical_height": float(event.logical_height),
                        "physical_width": int(event.physical_width),
                        "physical_height": int(event.physical_height),
                        "dpi_scale": float(event.dpi_scale),
                    },
                )
                continue
            if isinstance(event, WindowFocusEvent):
                hub.emit_fast(
                    category="window",
                    name="window.focus",
                    tick=tick,
                    value={"focused": bool(event.focused)},
                )
                continue
            if isinstance(event, WindowMinimizeEvent):
                hub.emit_fast(
                    category="window",
                    name="window.minimize",
                    tick=tick,
                    value={"minimized": bool(event.minimized)},
                )
                continue
            if isinstance(event, WindowCloseEvent):
                hub.emit_fast(
                    category="window",
                    name="window.close_requested",
                    tick=tick,
                    value={"requested": bool(event.requested)},
                )
                self._host.close()
        if resize_events_seen > 0:
            resize_telemetry = self._window.consume_resize_telemetry()
            hub.emit_fast(
                category="window",
                name="window.resize_burst",
                tick=tick,
                value={
                    "resize_events_seen": int(resize_events_seen),
                    **{
                        str(key): int(value)
                        for key, value in resize_telemetry.items()
                        if isinstance(value, (int, float))
                    },
                },
            )

    def _build_input_snapshot(self) -> InputSnapshot:
        window_raw_input = self._window.poll_input_events()
        if window_raw_input:
            self._input.consume_window_input_events(window_raw_input)
        return self._input.build_input_snapshot(frame_index=self._host.current_frame_index())

    def _dispatch_input_snapshot(self, snapshot: InputSnapshot) -> None:
        changed = self._host.handle_input_snapshot(snapshot)
        if changed:
            self._renderer.invalidate()


def create_window_frontend(
    *,
    renderer: RenderAPI,
    window: WindowPort,
    input_controller: InputController,
    host: EngineHost,
) -> HostedWindowFrontend:
    """Build frontend window from precomposed engine host/runtime services."""
    return HostedWindowFrontend(
        renderer=renderer,
        window=window,
        input_controller=input_controller,
        host=host,
    )

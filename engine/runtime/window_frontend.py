"""Engine runtime window frontend."""

from __future__ import annotations

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
        canvas = getattr(self._window, "canvas", None)
        request_draw = getattr(canvas, "request_draw", None)
        if callable(request_draw):
            request_draw(self._draw_frame)
            request_draw()
        self._window.run_loop()

    def _draw_frame(self) -> None:
        self._note_frame_reason("draw")
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
        hub = getattr(self._host, "diagnostics_hub", None)
        tick = int(self._host.current_frame_index())
        for event in events:
            if isinstance(event, WindowResizeEvent):
                self._note_frame_reason("window:resize")
                apply_window_resize = getattr(self._renderer, "apply_window_resize", None)
                if callable(apply_window_resize):
                    apply_window_resize(event)
                if hub is not None and hasattr(hub, "emit_fast"):
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
                if hub is not None and hasattr(hub, "emit_fast"):
                    hub.emit_fast(
                        category="window",
                        name="window.focus",
                        tick=tick,
                        value={"focused": bool(event.focused)},
                    )
                continue
            if isinstance(event, WindowMinimizeEvent):
                if hub is not None and hasattr(hub, "emit_fast"):
                    hub.emit_fast(
                        category="window",
                        name="window.minimize",
                        tick=tick,
                        value={"minimized": bool(event.minimized)},
                    )
                continue
            if isinstance(event, WindowCloseEvent):
                if hub is not None and hasattr(hub, "emit_fast"):
                    hub.emit_fast(
                        category="window",
                        name="window.close_requested",
                        tick=tick,
                        value={"requested": bool(event.requested)},
                    )
                self._host.close()

    def _build_input_snapshot(self) -> InputSnapshot:
        window_raw_input = self._window.poll_input_events()
        if window_raw_input:
            self._input.consume_window_input_events(window_raw_input)
        return self._input.build_input_snapshot(frame_index=self._host.current_frame_index())

    def _dispatch_input_snapshot(self, snapshot: InputSnapshot) -> None:
        changed = self._host.handle_input_snapshot(snapshot)
        if snapshot.pointer_events:
            self._note_frame_reason("input:pointer")
        if snapshot.key_events:
            self._note_frame_reason("input:key")
        if snapshot.wheel_events:
            self._note_frame_reason("input:wheel")
        for pointer_event in snapshot.pointer_events:
            event_type = getattr(pointer_event, "event_type", "")
            if isinstance(event_type, str) and event_type.strip():
                normalized_type = event_type.strip().lower().replace(" ", "_")
                self._note_frame_reason(f"input:pointer:{normalized_type}")
        if changed:
            self._note_frame_reason("input:changed")
            self._renderer.invalidate()

    def _note_frame_reason(self, reason: str) -> None:
        note = getattr(self._renderer, "note_frame_reason", None)
        if callable(note):
            note(reason)


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


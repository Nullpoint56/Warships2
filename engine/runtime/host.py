"""Engine-hosted runtime shell for game module execution."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.render import RenderAPI
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.runtime.debug_config import enabled_metrics, enabled_overlay
from engine.runtime.metrics import MetricsSnapshot, create_metrics_collector
from engine.runtime.scheduler import Scheduler
from engine.runtime.time import FrameClock
from engine.ui_runtime.debug_overlay import DebugOverlay

_LOG = logging.getLogger("engine.runtime")
_OVERLAY_TOGGLE_KEY = "f3"


@dataclass(frozen=True, slots=True)
class EngineHostConfig:
    """Host runtime configuration."""

    window_mode: str = "windowed"
    width: int = 1280
    height: int = 800


class EngineHost(HostControl):
    """Lifecycle shell for engine-hosted runtime migration."""

    def __init__(
        self,
        module: GameModule,
        config: EngineHostConfig | None = None,
        render_api: RenderAPI | None = None,
    ) -> None:
        self._module = module
        self._config = config or EngineHostConfig()
        self._frame_index = 0
        self._closed = False
        self._started = False
        self._clock = FrameClock()
        self._scheduler = Scheduler()
        self._render_api = render_api
        self._debug_overlay = DebugOverlay() if enabled_overlay() else None
        self._debug_overlay_visible = False
        self._metrics_collector = create_metrics_collector(enabled=enabled_metrics())

    @property
    def config(self) -> EngineHostConfig:
        return self._config

    @property
    def metrics_collector(self) -> object:
        return self._metrics_collector

    @property
    def metrics_snapshot(self) -> MetricsSnapshot:
        return self._metrics_collector.snapshot()

    def start(self) -> None:
        """Start module lifecycle."""
        if self._started:
            return
        self._started = True
        self._module.on_start(self)

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        return self._module.on_pointer_event(event)

    def handle_key_event(self, event: KeyEvent) -> bool:
        if self._debug_overlay is not None and self._is_overlay_toggle_event(event):
            self._debug_overlay_visible = not self._debug_overlay_visible
            if self._render_api is not None and hasattr(self._render_api, "invalidate"):
                self._render_api.invalidate()
            return True
        return self._module.on_key_event(event)

    def handle_wheel_event(self, event: WheelEvent) -> bool:
        return self._module.on_wheel_event(event)

    def frame(self) -> None:
        """Execute one frame callback."""
        if not self._started:
            self.start()
        if self._closed:
            return
        time_context = self._clock.next(self._frame_index)
        self._metrics_collector.begin_frame(self._frame_index)
        self._scheduler.advance(time_context.delta_seconds)
        enqueued_count, dequeued_count = self._scheduler.consume_activity_counts()
        if hasattr(self._metrics_collector, "set_scheduler_activity"):
            self._metrics_collector.set_scheduler_activity(enqueued_count, dequeued_count)
        self._metrics_collector.set_scheduler_queue_size(self._scheduler.queued_task_count)
        if self._closed:
            self._metrics_collector.end_frame(time_context.delta_seconds * 1000.0)
            return
        self._module.on_frame(
            HostFrameContext(
                frame_index=self._frame_index,
                delta_seconds=time_context.delta_seconds,
                elapsed_seconds=time_context.elapsed_seconds,
            )
        )
        self._metrics_collector.end_frame(time_context.delta_seconds * 1000.0)
        if self._debug_overlay is not None and self._debug_overlay_visible and self._render_api is not None:
            diagnostics_summary = None
            get_diag = getattr(self._render_api, "ui_diagnostics_summary", None)
            if callable(get_diag):
                diagnostics_summary = get_diag()
            self._debug_overlay.draw(
                self._render_api,
                self._metrics_collector.snapshot(),
                ui_diagnostics=diagnostics_summary,
            )
        if _LOG.isEnabledFor(logging.DEBUG):
            snapshot = self._metrics_collector.snapshot()
            if snapshot.last_frame is not None:
                _LOG.debug(
                    "frame_metrics frame=%d dt_ms=%.3f fps=%.2f sched_q=%d events=%d top=%s",
                    snapshot.last_frame.frame_index,
                    snapshot.last_frame.dt_ms,
                    snapshot.rolling_fps,
                    snapshot.last_frame.scheduler_queue_size,
                    snapshot.last_frame.event_publish_count,
                    snapshot.top_systems_last_frame,
                )
        self._frame_index += 1
        if self._module.should_close():
            self.close()

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a one-shot callback in host runtime time."""
        return self._scheduler.call_later(delay_seconds, callback)

    def call_every(self, interval_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a recurring callback in host runtime time."""
        return self._scheduler.call_every(interval_seconds, callback)

    def cancel_task(self, task_id: int) -> None:
        """Cancel a previously scheduled task."""
        self._scheduler.cancel(task_id)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._module.on_shutdown()

    def is_closed(self) -> bool:
        return self._closed

    @staticmethod
    def _is_overlay_toggle_event(event: KeyEvent) -> bool:
        return event.event_type == "key_down" and event.value.strip().lower() == _OVERLAY_TOGGLE_KEY

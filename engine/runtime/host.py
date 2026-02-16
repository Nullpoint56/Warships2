"""Engine-hosted runtime shell for game module execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.runtime.scheduler import Scheduler
from engine.runtime.time import FrameClock


@dataclass(frozen=True, slots=True)
class EngineHostConfig:
    """Host runtime configuration."""

    window_mode: str = "windowed"
    width: int = 1280
    height: int = 800


class EngineHost(HostControl):
    """Lifecycle shell for engine-hosted runtime migration."""

    def __init__(self, module: GameModule, config: EngineHostConfig | None = None) -> None:
        self._module = module
        self._config = config or EngineHostConfig()
        self._frame_index = 0
        self._closed = False
        self._started = False
        self._clock = FrameClock()
        self._scheduler = Scheduler()

    @property
    def config(self) -> EngineHostConfig:
        return self._config

    def start(self) -> None:
        """Start module lifecycle."""
        if self._started:
            return
        self._started = True
        self._module.on_start(self)

    def handle_pointer_event(self, event: PointerEvent) -> bool:
        return self._module.on_pointer_event(event)

    def handle_key_event(self, event: KeyEvent) -> bool:
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
        self._scheduler.advance(time_context.delta_seconds)
        if self._closed:
            return
        self._module.on_frame(
            HostFrameContext(
                frame_index=self._frame_index,
                delta_seconds=time_context.delta_seconds,
                elapsed_seconds=time_context.elapsed_seconds,
            )
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

"""Engine-hosted runtime shell for game module execution."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent


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
        self._module.on_frame(HostFrameContext(frame_index=self._frame_index))
        self._frame_index += 1
        if self._module.should_close():
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._module.on_shutdown()

    def is_closed(self) -> bool:
        return self._closed

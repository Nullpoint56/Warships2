"""Engine-hosted game module contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from engine.api.input_snapshot import InputSnapshot
from engine.api.render_snapshot import RenderSnapshot


@dataclass(frozen=True, slots=True)
class HostFrameContext:
    """Per-frame context passed from engine host to game module."""

    frame_index: int
    delta_seconds: float
    elapsed_seconds: float


@runtime_checkable
class HostControl(Protocol):
    """Host control surface exposed to game modules."""

    def close(self) -> None:
        """Request host shutdown."""

    def call_later(self, delay_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a one-shot callback in host runtime time."""

    def call_every(self, interval_seconds: float, callback: Callable[[], None]) -> int:
        """Schedule a recurring callback in host runtime time."""

    def cancel_task(self, task_id: int) -> None:
        """Cancel a previously scheduled task."""


@runtime_checkable
class GameModule(Protocol):
    """Engine-facing game module lifecycle and event hooks."""

    def on_start(self, host: HostControl) -> None:
        """Initialize game module and capture host control if needed."""

    def on_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        """Handle immutable per-frame input snapshot. Return whether state changed."""

    def simulate(self, context: HostFrameContext) -> None:
        """Advance simulation for one frame."""

    def build_render_snapshot(self) -> RenderSnapshot | None:
        """Build immutable render snapshot for renderer consumption."""

    def should_close(self) -> bool:
        """Return whether host should stop."""

    def on_shutdown(self) -> None:
        """Release resources and finalize state."""

"""Public runtime context API."""

from __future__ import annotations

from typing import Protocol

from engine.api.render import RenderAPI


class LayoutPort(Protocol):
    """Opaque layout boundary contract."""


class InputControllerPort(Protocol):
    """Opaque input-controller boundary contract."""


class FrameClockPort(Protocol):
    """Opaque frame-clock boundary contract."""


class SchedulerPort(Protocol):
    """Opaque scheduler boundary contract."""


class RuntimeContext(Protocol):
    """Shared runtime context passed across engine modules."""

    render_api: RenderAPI | None
    layout: LayoutPort | None
    input_controller: InputControllerPort | None
    frame_clock: FrameClockPort | None
    scheduler: SchedulerPort | None
    services: dict[str, "ServiceLike"]

    def provide(self, name: str, service: "ServiceLike") -> None:
        """Register a named service."""

    def get(self, name: str) -> "ServiceLike | None":
        """Return a named service if present."""

    def require(self, name: str) -> "ServiceLike":
        """Return named service or raise KeyError."""


class ServiceLike(Protocol):
    """Opaque service contract for runtime context boundaries."""

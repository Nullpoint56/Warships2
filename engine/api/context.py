"""Public runtime context API."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from engine.api.render import RenderAPI


@runtime_checkable
class LayoutPort(Protocol):
    """Opaque layout boundary contract."""


@runtime_checkable
class InputControllerPort(Protocol):
    """Opaque input-controller boundary contract."""


@runtime_checkable
class FrameClockPort(Protocol):
    """Opaque frame-clock boundary contract."""


@runtime_checkable
class SchedulerPort(Protocol):
    """Opaque scheduler boundary contract."""


@runtime_checkable
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

"""Public runtime context API."""

from __future__ import annotations

from typing import Protocol

from engine.api.render import RenderAPI


class RuntimeContext(Protocol):
    """Shared runtime context passed across engine modules."""

    render_api: RenderAPI | None
    layout: object | None
    input_controller: object | None
    frame_clock: object | None
    scheduler: object | None
    services: dict[str, object]

    def provide(self, name: str, service: object) -> None:
        """Register a named service."""

    def get(self, name: str) -> object | None:
        """Return a named service if present."""

    def require(self, name: str) -> object:
        """Return named service or raise KeyError."""


def create_runtime_context(
    *,
    render_api: RenderAPI | None = None,
    layout: object | None = None,
    input_controller: object | None = None,
    frame_clock: object | None = None,
    scheduler: object | None = None,
) -> RuntimeContext:
    """Create default runtime-context implementation."""
    from engine.runtime.context import RuntimeContextImpl

    return RuntimeContextImpl(
        render_api=render_api,
        layout=layout,
        input_controller=input_controller,
        frame_clock=frame_clock,
        scheduler=scheduler,
    )

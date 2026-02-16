"""Runtime context implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.api.render import RenderAPI


@dataclass(slots=True)
class RuntimeContextImpl:
    """Default mutable runtime context."""

    render_api: RenderAPI | None = None
    layout: object | None = None
    input_controller: object | None = None
    frame_clock: object | None = None
    scheduler: object | None = None
    services: dict[str, object] = field(default_factory=dict)

    def provide(self, name: str, service: object) -> None:
        """Register or replace a named service."""
        normalized = name.strip()
        if not normalized:
            raise ValueError("service name must not be empty")
        self.services[normalized] = service

    def get(self, name: str) -> object | None:
        """Return named service if present."""
        return self.services.get(name)

    def require(self, name: str) -> object:
        """Return named service or raise KeyError."""
        value = self.get(name)
        if value is None:
            raise KeyError(f"missing runtime service: {name}")
        return value

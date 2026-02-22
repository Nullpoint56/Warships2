"""Public module-graph API contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from engine.api.context import RuntimeContext


@runtime_checkable
class RuntimeModule(Protocol):
    """Lifecycle hooks for engine runtime modules."""

    def start(self, context: RuntimeContext) -> None:
        """Initialize module with shared runtime context."""

    def update(self, context: RuntimeContext) -> None:
        """Execute one update tick."""

    def shutdown(self, context: RuntimeContext) -> None:
        """Release module resources."""


@dataclass(frozen=True, slots=True)
class ModuleNode:
    """Module registration entry."""

    module_id: str
    module: RuntimeModule
    depends_on: tuple[str, ...] = ()


@runtime_checkable
class ModuleGraph(Protocol):
    """Ordered lifecycle executor for runtime modules."""

    def add_node(self, node: ModuleNode) -> None:
        """Register one module node."""

    def start_all(self, context: RuntimeContext) -> None:
        """Start registered modules in dependency order."""

    def update_all(self, context: RuntimeContext) -> None:
        """Update started modules in dependency order."""

    def shutdown_all(self, context: RuntimeContext) -> None:
        """Shutdown started modules in reverse dependency order."""

    def execution_order(self) -> tuple[str, ...]:
        """Return current dependency order."""

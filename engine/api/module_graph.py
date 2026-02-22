"""Public module-graph API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
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


class ModuleGraph(ABC):
    """Ordered lifecycle executor for runtime modules."""

    @abstractmethod
    def add_node(self, node: ModuleNode) -> None:
        """Register one module node."""

    @abstractmethod
    def start_all(self, context: RuntimeContext) -> None:
        """Start registered modules in dependency order."""

    @abstractmethod
    def update_all(self, context: RuntimeContext) -> None:
        """Update started modules in dependency order."""

    @abstractmethod
    def shutdown_all(self, context: RuntimeContext) -> None:
        """Shutdown started modules in reverse dependency order."""

    @abstractmethod
    def execution_order(self) -> tuple[str, ...]:
        """Return current dependency order."""

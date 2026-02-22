"""Module graph implementation for runtime lifecycle composition."""

from __future__ import annotations

from collections import deque

from engine.api.context import RuntimeContext
from engine.api.module_graph import ModuleGraph, ModuleNode


class RuntimeModuleGraph(ModuleGraph):
    """Dependency-ordered lifecycle runner for runtime modules."""

    def __init__(self) -> None:
        self._nodes: dict[str, ModuleNode] = {}
        self._started: set[str] = set()
        self._cached_order: tuple[str, ...] | None = None

    def add_node(self, node: ModuleNode) -> None:
        """Register one node; invalidates cached execution order."""
        module_id = node.module_id.strip()
        if not module_id:
            raise ValueError("module_id must not be empty")
        if module_id in self._nodes:
            raise ValueError(f"duplicate module_id: {module_id}")
        self._nodes[module_id] = ModuleNode(
            module_id=module_id,
            module=node.module,
            depends_on=tuple(dep.strip() for dep in node.depends_on),
        )
        self._cached_order = None

    def start_all(self, context: RuntimeContext) -> None:
        """Start modules in dependency order (idempotent per module)."""
        for module_id in self.execution_order():
            if module_id in self._started:
                continue
            self._nodes[module_id].module.start(context)
            self._started.add(module_id)

    def update_all(self, context: RuntimeContext) -> None:
        """Update started modules in dependency order."""
        for module_id in self.execution_order():
            if module_id not in self._started:
                continue
            self._nodes[module_id].module.update(context)

    def shutdown_all(self, context: RuntimeContext) -> None:
        """Shutdown started modules in reverse dependency order."""
        for module_id in reversed(self.execution_order()):
            if module_id not in self._started:
                continue
            self._nodes[module_id].module.shutdown(context)
            self._started.remove(module_id)

    def execution_order(self) -> tuple[str, ...]:
        """Compute dependency order and validate the graph."""
        if self._cached_order is not None:
            return self._cached_order

        indegree: dict[str, int] = {module_id: 0 for module_id in self._nodes}
        outgoing: dict[str, list[str]] = {module_id: [] for module_id in self._nodes}

        for module_id, node in self._nodes.items():
            for dependency in node.depends_on:
                if dependency not in self._nodes:
                    raise KeyError(f"unknown dependency '{dependency}' for module '{module_id}'")
                indegree[module_id] += 1
                outgoing[dependency].append(module_id)

        queue = deque(sorted(mid for mid, degree in indegree.items() if degree == 0))
        ordered: list[str] = []

        while queue:
            current = queue.popleft()
            ordered.append(current)
            for target in outgoing[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)

        if len(ordered) != len(self._nodes):
            raise ValueError("module dependency cycle detected")

        self._cached_order = tuple(ordered)
        return self._cached_order

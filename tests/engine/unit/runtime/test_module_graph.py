from __future__ import annotations

import pytest

from engine.api.module_graph import ModuleNode
from engine.runtime.context import RuntimeContextImpl
from engine.runtime.module_graph import RuntimeModuleGraph


class _Module:
    def __init__(self, module_id: str, events: list[str]) -> None:
        self._id = module_id
        self._events = events

    def start(self, context) -> None:
        _ = context
        self._events.append(f"start:{self._id}")

    def update(self, context) -> None:
        _ = context
        self._events.append(f"update:{self._id}")

    def shutdown(self, context) -> None:
        _ = context
        self._events.append(f"shutdown:{self._id}")


def test_module_graph_runs_start_update_shutdown_in_dependency_order() -> None:
    events: list[str] = []
    graph = RuntimeModuleGraph()
    graph.add_node(ModuleNode("assets", _Module("assets", events)))
    graph.add_node(ModuleNode("ui", _Module("ui", events), depends_on=("assets",)))
    graph.add_node(ModuleNode("hud", _Module("hud", events), depends_on=("ui",)))
    context = RuntimeContextImpl()

    graph.start_all(context)
    graph.update_all(context)
    graph.shutdown_all(context)

    assert events == [
        "start:assets",
        "start:ui",
        "start:hud",
        "update:assets",
        "update:ui",
        "update:hud",
        "shutdown:hud",
        "shutdown:ui",
        "shutdown:assets",
    ]


def test_module_graph_detects_unknown_dependency() -> None:
    graph = RuntimeModuleGraph()
    graph.add_node(ModuleNode("ui", _Module("ui", []), depends_on=("missing",)))
    with pytest.raises(KeyError):
        graph.execution_order()


def test_module_graph_detects_cycle() -> None:
    graph = RuntimeModuleGraph()
    graph.add_node(ModuleNode("a", _Module("a", []), depends_on=("b",)))
    graph.add_node(ModuleNode("b", _Module("b", []), depends_on=("a",)))
    with pytest.raises(ValueError):
        graph.execution_order()


def test_module_graph_rejects_duplicate_module_id() -> None:
    graph = RuntimeModuleGraph()
    graph.add_node(ModuleNode("ui", _Module("ui", [])))
    with pytest.raises(ValueError):
        graph.add_node(ModuleNode("ui", _Module("ui2", [])))

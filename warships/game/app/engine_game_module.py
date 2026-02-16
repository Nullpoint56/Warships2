"""Warships GameModule adapter for engine-hosted runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from engine.api.context import RuntimeContext, create_runtime_context
from engine.api.events import Subscription, create_event_bus
from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.module_graph import ModuleNode, RuntimeModule, create_module_graph
from engine.api.ui_framework import UIFramework
from engine.input.input_controller import KeyEvent, PointerEvent, WheelEvent
from warships.game.app.controller import GameController
from warships.game.ui.game_view import GameView


@dataclass(frozen=True, slots=True)
class _CloseRequested:
    """Internal runtime event used to decouple close signaling."""


class _FrameworkSyncModule(RuntimeModule):
    """Sync framework state before rendering."""

    def start(self, context: RuntimeContext) -> None:
        _ = context

    def update(self, context: RuntimeContext) -> None:
        framework = cast(UIFramework, context.require("framework"))
        framework.sync_ui_state()

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class _ViewRenderModule(RuntimeModule):
    """Render frame and store transient UI data."""

    def start(self, context: RuntimeContext) -> None:
        context.provide("debug_labels", [])

    def update(self, context: RuntimeContext) -> None:
        controller = cast(GameController, context.require("controller"))
        view = cast(GameView, context.require("view"))
        debug_ui = cast(bool, context.require("debug_ui"))
        labels = cast(list[str], context.require("debug_labels"))
        ui = controller.ui_state()
        next_labels = view.render(ui, debug_ui, labels)
        context.provide("debug_labels", next_labels)
        context.provide("ui_state", ui)

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class _CloseLifecycleModule(RuntimeModule):
    """Request close when UI enters closing state."""

    def start(self, context: RuntimeContext) -> None:
        _ = context

    def update(self, context: RuntimeContext) -> None:
        ui_state = context.get("ui_state")
        if ui_state is None or not getattr(ui_state, "is_closing", False):
            return
        request_close = cast(Callable[[], None], context.require("request_close"))
        request_close()

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class WarshipsGameModule(GameModule):
    """Engine-facing adapter that delegates to existing Warships app graph."""

    def __init__(
        self,
        controller: GameController,
        framework: UIFramework,
        view: GameView,
        debug_ui: bool,
    ) -> None:
        self._controller = controller
        self._framework = framework
        self._view = view
        self._debug_ui = debug_ui
        self._host: HostControl | None = None
        self._events = create_event_bus()
        self._close_subscription: Subscription | None = None
        self._close_task_id: int | None = None
        self._context = create_runtime_context()
        self._context.provide("controller", controller)
        self._context.provide("framework", framework)
        self._context.provide("view", view)
        self._context.provide("debug_ui", debug_ui)
        self._context.provide("request_close", self._schedule_close_request)
        self._graph = create_module_graph()
        self._graph.add_node(ModuleNode("framework_sync", _FrameworkSyncModule()))
        self._graph.add_node(
            ModuleNode("view_render", _ViewRenderModule(), depends_on=("framework_sync",))
        )
        self._graph.add_node(
            ModuleNode("close_lifecycle", _CloseLifecycleModule(), depends_on=("view_render",))
        )

    def on_start(self, host: HostControl) -> None:
        self._host = host
        self._context.provide("host", host)
        self._close_subscription = self._events.subscribe(_CloseRequested, self._on_close_requested)
        self._graph.start_all(self._context)

    def on_pointer_event(self, event: PointerEvent) -> bool:
        return self._framework.handle_pointer_event(event)

    def on_key_event(self, event: KeyEvent) -> bool:
        return self._framework.handle_key_event(event)

    def on_wheel_event(self, event: WheelEvent) -> bool:
        return self._framework.handle_wheel_event(event)

    def on_frame(self, context: HostFrameContext) -> None:
        self._context.provide("frame_context", context)
        self._graph.update_all(self._context)

    def should_close(self) -> bool:
        return False

    def on_shutdown(self) -> None:
        self._graph.shutdown_all(self._context)
        if self._host is not None and self._close_task_id is not None:
            self._host.cancel_task(self._close_task_id)
            self._close_task_id = None
        if self._close_subscription is not None:
            self._events.unsubscribe(self._close_subscription)
            self._close_subscription = None
        return

    def _schedule_close_request(self) -> None:
        if self._host is None or self._close_task_id is not None:
            return
        self._close_task_id = self._host.call_later(0.0, self._emit_close_requested)

    def _emit_close_requested(self) -> None:
        self._close_task_id = None
        self._events.publish(_CloseRequested())

    def _on_close_requested(self, _event: _CloseRequested) -> None:
        if self._host is None:
            return
        self._host.close()

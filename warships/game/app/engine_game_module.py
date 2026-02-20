"""Warships GameModule adapter for engine-hosted runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from engine.api.context import RuntimeContext, create_runtime_context
from engine.api.events import Subscription, create_event_bus
from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.gameplay import (
    GameplaySystem,
    StateStore,
    SystemSpec,
    UpdateLoop,
    create_state_store,
    create_update_loop,
)
from engine.api.input_events import KeyEvent, PointerEvent, WheelEvent
from engine.api.input_snapshot import InputSnapshot
from engine.api.module_graph import ModuleNode, RuntimeModule, create_module_graph
from engine.api.render_snapshot import RenderSnapshot
from engine.api.ui_framework import UIFramework
from warships.game.app.controller import GameController
from warships.game.ui.game_view import GameView


@dataclass(frozen=True, slots=True)
class _CloseRequested:
    """Internal runtime event used to decouple close signaling."""


@dataclass(frozen=True, slots=True)
class _FrameState:
    """Per-frame transient state stored in gameplay state-store."""

    debug_labels: list[str]
    ui_state: object | None = None


class _FrameworkSyncSystem(GameplaySystem):
    """Sync framework state before rendering."""

    def start(self, context: RuntimeContext) -> None:
        _ = context

    def update(self, context: RuntimeContext, delta_seconds: float) -> None:
        _ = delta_seconds
        framework = cast(UIFramework, context.require("framework"))
        framework.sync_ui_state()

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class _ViewRenderSystem(GameplaySystem):
    """Render frame and update transient frame state."""

    def start(self, context: RuntimeContext) -> None:
        _ = context

    def update(self, context: RuntimeContext, delta_seconds: float) -> None:
        _ = delta_seconds
        controller = cast(GameController, context.require("controller"))
        view = cast(GameView, context.require("view"))
        debug_ui = cast(bool, context.require("debug_ui"))
        state_store = cast(StateStore[_FrameState], context.require("frame_state_store"))
        frame_state = state_store.get()
        ui = controller.ui_state()
        next_labels = view.render(ui, debug_ui, frame_state.debug_labels)
        state_store.set(_FrameState(debug_labels=next_labels, ui_state=ui))

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class _CloseLifecycleSystem(GameplaySystem):
    """Request close when UI enters closing state."""

    def start(self, context: RuntimeContext) -> None:
        _ = context

    def update(self, context: RuntimeContext, delta_seconds: float) -> None:
        _ = delta_seconds
        state_store = cast(StateStore[_FrameState], context.require("frame_state_store"))
        ui_state = state_store.get().ui_state
        if ui_state is None or not getattr(ui_state, "is_closing", False):
            return
        request_close = cast(Callable[[], None], context.require("request_close"))
        request_close()

    def shutdown(self, context: RuntimeContext) -> None:
        _ = context


class _GameplayLoopModule(RuntimeModule):
    """Adapter that drives gameplay update-loop from module graph."""

    def __init__(self, update_loop: UpdateLoop) -> None:
        self._update_loop = update_loop

    def start(self, context: RuntimeContext) -> None:
        self._update_loop.start(context)

    def update(self, context: RuntimeContext) -> None:
        frame_context = cast(HostFrameContext | None, context.get("frame_context"))
        delta_seconds = frame_context.delta_seconds if frame_context is not None else 0.0
        self._update_loop.step(context, delta_seconds)

    def shutdown(self, context: RuntimeContext) -> None:
        self._update_loop.shutdown(context)


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
        self._frame_state_store = create_state_store(_FrameState(debug_labels=[]))
        self._context.provide("frame_state_store", self._frame_state_store)
        self._update_loop = create_update_loop()
        self._update_loop.add_system(SystemSpec("framework_sync", _FrameworkSyncSystem(), order=0))
        self._update_loop.add_system(SystemSpec("view_render", _ViewRenderSystem(), order=10))
        self._update_loop.add_system(
            SystemSpec("close_lifecycle", _CloseLifecycleSystem(), order=20)
        )
        self._graph = create_module_graph()
        self._graph.add_node(ModuleNode("gameplay_loop", _GameplayLoopModule(self._update_loop)))

    def on_start(self, host: HostControl) -> None:
        self._host = host
        self._context.provide("host", host)
        metrics_collector = getattr(host, "metrics_collector", None)
        if metrics_collector is not None:
            self._context.provide("metrics_collector", metrics_collector)
            if hasattr(self._events, "set_metrics_collector"):
                self._events.set_metrics_collector(metrics_collector)
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

    def on_input_snapshot(self, snapshot: InputSnapshot) -> None:
        self._context.provide("input_snapshot", snapshot)

    def simulate(self, context: HostFrameContext) -> None:
        self.on_frame(context)

    def build_render_snapshot(self) -> RenderSnapshot | None:
        return None

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

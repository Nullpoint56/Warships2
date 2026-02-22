"""Runtime-agnostic default implementations for engine API contracts."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar, cast

from engine.api.action_dispatch import ActionDispatcher, DirectActionHandler, PrefixedActionHandler
from engine.api.context import (
    FrameClockPort,
    InputControllerPort,
    LayoutPort,
    RuntimeContext,
    SchedulerPort,
    ServiceLike,
)
from engine.api.events import EventBus, EventPayload, Subscription
from engine.api.flow import FlowContext, FlowPayload, FlowProgram, FlowTransition
from engine.api.gameplay import SystemSpec, UpdateLoop
from engine.api.interaction_modes import InteractionMode, InteractionModeMachine
from engine.api.module_graph import ModuleGraph, ModuleNode
from engine.api.render import RenderAPI
from engine.api.screens import ScreenData, ScreenLayer, ScreenStack

TState = TypeVar("TState")
TEvent = TypeVar("TEvent")


@dataclass(frozen=True, slots=True)
class SdkActionDispatcher(ActionDispatcher):
    direct_handlers: dict[str, DirectActionHandler]
    prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...]

    def dispatch(self, action_id: str) -> bool | None:
        handler = self.direct_handlers.get(action_id)
        if handler is not None:
            return handler()
        for prefix, prefixed_handler in self.prefixed_handlers:
            if action_id.startswith(prefix):
                return prefixed_handler(action_id[len(prefix) :])
        return None


class SdkInteractionModeMachine(InteractionModeMachine):
    def __init__(self) -> None:
        self._modes: dict[str, InteractionMode] = {}
        self.register(InteractionMode("default", True, True, True))
        self.register(InteractionMode("modal", True, True, False))
        self.register(InteractionMode("captured", True, True, True))
        self._current = "default"

    @property
    def current_mode(self) -> str:
        return self._current

    def register(self, mode: InteractionMode) -> None:
        normalized = mode.name.strip().lower()
        if not normalized:
            raise ValueError("mode name must not be empty")
        self._modes[normalized] = InteractionMode(
            name=normalized,
            allow_pointer=mode.allow_pointer,
            allow_keyboard=mode.allow_keyboard,
            allow_wheel=mode.allow_wheel,
        )

    def set_mode(self, mode_name: str) -> None:
        normalized = mode_name.strip().lower()
        if normalized not in self._modes:
            raise KeyError(f"unknown mode: {mode_name}")
        self._current = normalized

    def allows_pointer(self) -> bool:
        return self._modes[self._current].allow_pointer

    def allows_keyboard(self) -> bool:
        return self._modes[self._current].allow_keyboard

    def allows_wheel(self) -> bool:
        return self._modes[self._current].allow_wheel


class SdkScreenStack(ScreenStack):
    def __init__(self) -> None:
        self._root: ScreenLayer | None = None
        self._overlays: list[ScreenLayer] = []

    def set_root(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        layer = ScreenLayer(screen_id=screen_id, kind="root", data=data)
        self._root = layer
        self._overlays.clear()
        return layer

    def push_overlay(self, screen_id: str, *, data: ScreenData | None = None) -> ScreenLayer:
        if self._root is None:
            raise RuntimeError("cannot push overlay without root screen")
        layer = ScreenLayer(screen_id=screen_id, kind="overlay", data=data)
        self._overlays.append(layer)
        return layer

    def pop_overlay(self) -> ScreenLayer | None:
        if not self._overlays:
            return None
        return self._overlays.pop()

    def clear_overlays(self) -> None:
        self._overlays.clear()

    def root(self) -> ScreenLayer | None:
        return self._root

    def top(self) -> ScreenLayer | None:
        if self._overlays:
            return self._overlays[-1]
        return self._root

    def layers(self) -> tuple[ScreenLayer, ...]:
        if self._root is None:
            return tuple(self._overlays)
        return (self._root, *self._overlays)


class SdkFlowProgram(FlowProgram[TState]):
    def __init__(self, transitions: tuple[FlowTransition[TState], ...]) -> None:
        self._transitions = transitions

    def resolve(
        self, current_state: TState, trigger: str, *, payload: FlowPayload | None = None
    ) -> TState | None:
        for transition in self._transitions:
            if transition.trigger != trigger:
                continue
            if transition.source is not None and transition.source != current_state:
                continue
            context = FlowContext(
                trigger=trigger,
                source=current_state,
                target=transition.target,
                payload=payload,
            )
            if transition.guard is not None and not transition.guard(context):
                continue
            if transition.before is not None:
                transition.before(context)
            if transition.after is not None:
                transition.after(context)
            return transition.target
        return None


@dataclass(slots=True)
class SdkRuntimeContext(RuntimeContext):
    render_api: RenderAPI | None = None
    layout: LayoutPort | None = None
    input_controller: InputControllerPort | None = None
    frame_clock: FrameClockPort | None = None
    scheduler: SchedulerPort | None = None
    services: dict[str, ServiceLike] = field(default_factory=dict)

    def provide(self, name: str, service: ServiceLike) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("service name must not be empty")
        self.services[normalized] = service

    def get(self, name: str) -> ServiceLike | None:
        return self.services.get(name)

    def require(self, name: str) -> ServiceLike:
        value = self.get(name)
        if value is None:
            raise KeyError(f"missing runtime service: {name}")
        return value


class SdkEventBus(EventBus):
    def __init__(self) -> None:
        self._next_id = 1
        self._subscriptions: dict[int, tuple[type[object], Callable[[object], None]]] = {}
        self._metrics_collector: object | None = None
        self._topic_counts_enabled = False

    def set_metrics_collector(
        self,
        metrics_collector: object | None,
        *,
        per_topic_counts_enabled: bool = False,
    ) -> None:
        self._metrics_collector = metrics_collector
        self._topic_counts_enabled = per_topic_counts_enabled

    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], None],
    ) -> Subscription:
        sub_id = self._next_id
        self._next_id += 1
        self._subscriptions[sub_id] = (event_type, cast(Callable[[object], None], handler))
        return Subscription(sub_id)

    def unsubscribe(self, subscription: Subscription) -> None:
        self._subscriptions.pop(subscription.id, None)

    def publish(self, event: EventPayload) -> int:
        metrics = self._metrics_collector
        if metrics is not None and hasattr(metrics, "increment_event_publish_count"):
            metrics.increment_event_publish_count(1)
            if self._topic_counts_enabled and hasattr(metrics, "increment_event_publish_topic"):
                metrics.increment_event_publish_topic(type(event).__name__, 1)
        invoked = 0
        for subscribed_type, handler in tuple(self._subscriptions.values()):
            if isinstance(event, subscribed_type):
                handler(event)
                invoked += 1
        return invoked


class SdkUpdateLoop(UpdateLoop):
    def __init__(self) -> None:
        self._systems: list[SystemSpec] = []
        self._started_ids: set[str] = set()
        self._cached_order: tuple[SystemSpec, ...] | None = None

    def add_system(self, spec: SystemSpec) -> None:
        normalized_id = spec.system_id.strip()
        if not normalized_id:
            raise ValueError("system_id must not be empty")
        if any(existing.system_id == normalized_id for existing in self._systems):
            raise ValueError(f"duplicate system_id: {normalized_id}")
        self._systems.append(SystemSpec(system_id=normalized_id, system=spec.system, order=spec.order))
        self._cached_order = None

    def start(self, context: RuntimeContext) -> None:
        for spec in self._ordered_systems():
            if spec.system_id in self._started_ids:
                continue
            spec.system.start(context)
            self._started_ids.add(spec.system_id)

    def step(self, context: RuntimeContext, delta_seconds: float) -> int:
        if delta_seconds < 0.0:
            raise ValueError("delta_seconds must be >= 0")
        ordered = self._ordered_systems()
        for spec in ordered:
            if spec.system_id not in self._started_ids:
                continue
            spec.system.update(context, delta_seconds)
        return 1 if ordered else 0

    def shutdown(self, context: RuntimeContext) -> None:
        for spec in reversed(self._ordered_systems()):
            if spec.system_id not in self._started_ids:
                continue
            spec.system.shutdown(context)
            self._started_ids.remove(spec.system_id)

    def _ordered_systems(self) -> tuple[SystemSpec, ...]:
        if self._cached_order is not None:
            return self._cached_order
        self._cached_order = tuple(sorted(self._systems, key=lambda item: (item.order, item.system_id)))
        return self._cached_order


class SdkModuleGraph(ModuleGraph):
    def __init__(self) -> None:
        self._nodes: dict[str, ModuleNode] = {}
        self._started: set[str] = set()
        self._cached_order: tuple[str, ...] | None = None

    def add_node(self, node: ModuleNode) -> None:
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
        for module_id in self.execution_order():
            if module_id in self._started:
                continue
            self._nodes[module_id].module.start(context)
            self._started.add(module_id)

    def update_all(self, context: RuntimeContext) -> None:
        for module_id in self.execution_order():
            if module_id not in self._started:
                continue
            self._nodes[module_id].module.update(context)

    def shutdown_all(self, context: RuntimeContext) -> None:
        for module_id in reversed(self.execution_order()):
            if module_id not in self._started:
                continue
            self._nodes[module_id].module.shutdown(context)
            self._started.remove(module_id)

    def execution_order(self) -> tuple[str, ...]:
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


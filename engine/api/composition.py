"""Public composition contracts for runtime-owned startup."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from collections.abc import Callable

from engine.api.action_dispatch import ActionDispatcher, DirectActionHandler, PrefixedActionHandler
from engine.api.app_port import EngineAppPort
from engine.api.context import RuntimeContext
from engine.api.events import EventBus
from engine.api.flow import FlowProgram, FlowTransition
from engine.api.game_module import GameModule
from engine.api.gameplay import UpdateLoop
from engine.api.hosted_runtime import HostedRuntimeConfig
from engine.api.interaction_modes import InteractionModeMachine
from engine.api.logging import EngineLoggingConfig
from engine.api.module_graph import ModuleGraph
from engine.api.render import RenderAPI
from engine.api.screens import ScreenStack
from engine.api.ui_primitives import GridLayout


@runtime_checkable
class EngineModule(Protocol):
    """Game-provided composition declaration consumed by engine runtime."""

    def runtime_config(self) -> HostedRuntimeConfig:
        """Return hosted runtime configuration."""

    def logging_config(self) -> EngineLoggingConfig:
        """Return logging configuration consumed by runtime."""

    def configure(self, binder: "ServiceBinder") -> None:
        """Register game bindings/overrides into composition binder."""


class ServiceResolver(ABC):
    """Runtime composition resolver contract."""

    @abstractmethod
    def resolve[TBinding: "BindingValue"](self, token: type[TBinding] | object) -> TBinding:
        """Resolve bound dependency by type token."""


class ServiceBinder(ServiceResolver, ABC):
    """Runtime composition binder contract."""

    @abstractmethod
    def bind_factory[TBinding: "BindingValue"](
        self, token: type[TBinding] | object, factory: Callable[[ServiceResolver], TBinding]
    ) -> None:
        """Bind/override dependency factory."""

    @abstractmethod
    def bind_instance[TBinding: "BindingValue"](
        self, token: type[TBinding] | object, instance: TBinding
    ) -> None:
        """Bind concrete singleton instance."""


class ControllerPort(Protocol):
    """Opaque controller boundary contract."""


class FrameworkPort(Protocol):
    """Opaque framework boundary contract."""


class ViewPort(Protocol):
    """Opaque view boundary contract."""


class BindingValue(Protocol):
    """Opaque DI binding value contract."""


@runtime_checkable
class ControllerFactory(Protocol):
    """Construct game controller root from resolver."""

    def __call__(self, resolver: ServiceResolver) -> ControllerPort: ...


@runtime_checkable
class StartupOverrideHook(Protocol):
    """Apply startup overrides to an already-built controller."""

    def __call__(self, controller: ControllerPort) -> None: ...


@runtime_checkable
class AppAdapterFactory(Protocol):
    """Create app adapter consumed by runtime framework."""

    def __call__(self, controller: ControllerPort) -> EngineAppPort: ...


@runtime_checkable
class ViewFactory(Protocol):
    """Create game view bound to app render adapter."""

    def __call__(self, renderer: RenderAPI, layout: GridLayout) -> ViewPort: ...


@dataclass(frozen=True, slots=True)
class GameModuleBuildRequest:
    """Input bundle for game module construction."""

    controller: ControllerPort
    framework: FrameworkPort
    view: ViewPort
    debug_ui: bool
    resolver: ServiceResolver


@runtime_checkable
class GameModuleFactory(Protocol):
    """Construct concrete game module for hosted runtime."""

    def __call__(self, request: GameModuleBuildRequest) -> GameModule: ...


@runtime_checkable
class ActionDispatcherFactory(Protocol):
    """Factory contract for action dispatcher instances."""

    def __call__(
        self,
        direct_handlers: dict[str, DirectActionHandler],
        prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...],
    ) -> ActionDispatcher: ...


@runtime_checkable
class FlowProgramFactory(Protocol):
    """Factory contract for typed flow program instances."""

    def __call__[TState](self, transitions: tuple[FlowTransition[TState], ...]) -> FlowProgram[TState]: ...

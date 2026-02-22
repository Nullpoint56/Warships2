"""Typed SDK service catalog and default binding registration."""

from __future__ import annotations

from engine.api.composition import (
    ActionDispatcherFactory,
    FlowProgramFactory,
    ServiceBinder,
)
from engine.api.context import RuntimeContext
from engine.api.events import EventBus
from engine.api.gameplay import UpdateLoop
from engine.api.interaction_modes import InteractionModeMachine
from engine.api.module_graph import ModuleGraph
from engine.api.screens import ScreenStack
from engine.sdk.defaults import (
    SdkActionDispatcher,
    SdkEventBus,
    SdkFlowProgram,
    SdkInteractionModeMachine,
    SdkModuleGraph,
    SdkRuntimeContext,
    SdkScreenStack,
    SdkUpdateLoop,
)

__all__ = [
    "bind_sdk_defaults",
]


def bind_sdk_defaults(binder: ServiceBinder) -> None:
    """Register canonical SDK default providers."""
    binder.bind_factory(ScreenStack, lambda _r: SdkScreenStack())
    binder.bind_factory(InteractionModeMachine, lambda _r: SdkInteractionModeMachine())
    binder.bind_factory(ActionDispatcherFactory, lambda _r: SdkActionDispatcher)
    binder.bind_factory(FlowProgramFactory, lambda _r: SdkFlowProgram)
    binder.bind_factory(RuntimeContext, lambda _r: SdkRuntimeContext())
    binder.bind_factory(EventBus, lambda _r: SdkEventBus())
    binder.bind_factory(UpdateLoop, lambda _r: SdkUpdateLoop())
    binder.bind_factory(ModuleGraph, lambda _r: SdkModuleGraph())

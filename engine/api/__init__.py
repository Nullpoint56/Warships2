"""Public engine API contracts."""

from engine.api.action_dispatch import (
    ActionDispatcher,
    DirectActionHandler,
    PrefixedActionHandler,
    create_action_dispatcher,
)
from engine.api.ai import (
    Agent,
    Blackboard,
    DecisionContext,
    best_action,
    combine_weighted_scores,
    create_blackboard,
    create_functional_agent,
    normalize_scores,
)
from engine.api.app_port import EngineAppPort
from engine.api.assets import AssetHandle, AssetRegistry, create_asset_registry
from engine.api.commands import Command, CommandMap, create_command_map
from engine.api.context import RuntimeContext, create_runtime_context
from engine.api.events import EventBus, Subscription, create_event_bus
from engine.api.flow import FlowContext, FlowMachine, FlowTransition, create_flow_machine
from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.gameplay import (
    GameplaySystem,
    StateSnapshot,
    StateStore,
    SystemSpec,
    UpdateLoop,
    create_state_store,
    create_update_loop,
)
from engine.api.hosted_runtime import HostedRuntimeConfig, run_pygfx_hosted_runtime
from engine.api.interaction_modes import (
    InteractionMode,
    InteractionModeMachine,
    create_interaction_mode_machine,
)
from engine.api.module_graph import ModuleGraph, ModuleNode, RuntimeModule, create_module_graph
from engine.api.render import RenderAPI
from engine.api.screens import ScreenLayer, ScreenStack, create_screen_stack
from engine.api.ui_framework import UIFramework, create_ui_framework

__all__ = [
    "ActionDispatcher",
    "Agent",
    "AssetHandle",
    "AssetRegistry",
    "Blackboard",
    "Command",
    "CommandMap",
    "DecisionContext",
    "DirectActionHandler",
    "EngineAppPort",
    "EventBus",
    "FlowContext",
    "FlowMachine",
    "FlowTransition",
    "GameModule",
    "GameplaySystem",
    "HostControl",
    "HostFrameContext",
    "HostedRuntimeConfig",
    "InteractionMode",
    "InteractionModeMachine",
    "ModuleGraph",
    "ModuleNode",
    "RenderAPI",
    "RuntimeContext",
    "RuntimeModule",
    "ScreenLayer",
    "ScreenStack",
    "StateSnapshot",
    "StateStore",
    "Subscription",
    "SystemSpec",
    "UIFramework",
    "UpdateLoop",
    "best_action",
    "combine_weighted_scores",
    "create_action_dispatcher",
    "create_asset_registry",
    "create_blackboard",
    "create_command_map",
    "create_event_bus",
    "create_functional_agent",
    "create_flow_machine",
    "create_interaction_mode_machine",
    "create_ui_framework",
    "normalize_scores",
    "run_pygfx_hosted_runtime",
    "create_module_graph",
    "create_runtime_context",
    "create_screen_stack",
    "create_state_store",
    "create_update_loop",
    "PrefixedActionHandler",
]

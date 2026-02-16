"""Public engine API contracts."""

from engine.api.app_port import EngineAppPort
from engine.api.assets import AssetHandle, AssetRegistry, create_asset_registry
from engine.api.commands import Command, CommandMap, create_command_map
from engine.api.events import EventBus, Subscription, create_event_bus
from engine.api.flow import FlowContext, FlowMachine, FlowTransition, create_flow_machine
from engine.api.game_module import GameModule, HostControl, HostFrameContext
from engine.api.interaction_modes import (
    InteractionMode,
    InteractionModeMachine,
    create_interaction_mode_machine,
)
from engine.api.render import RenderAPI
from engine.api.screens import ScreenLayer, ScreenStack, create_screen_stack

__all__ = [
    "AssetHandle",
    "AssetRegistry",
    "Command",
    "CommandMap",
    "EngineAppPort",
    "EventBus",
    "FlowContext",
    "FlowMachine",
    "FlowTransition",
    "GameModule",
    "HostControl",
    "HostFrameContext",
    "InteractionMode",
    "InteractionModeMachine",
    "RenderAPI",
    "ScreenLayer",
    "ScreenStack",
    "Subscription",
    "create_asset_registry",
    "create_command_map",
    "create_event_bus",
    "create_flow_machine",
    "create_interaction_mode_machine",
    "create_screen_stack",
]

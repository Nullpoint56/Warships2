"""Warships engine module declaration for runtime-owned composition."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import cast

from engine.api.composition import (
    ActionDispatcherFactory,
    AppAdapterFactory,
    ControllerPort,
    ControllerFactory,
    EngineModule,
    FlowProgramFactory,
    GameModuleBuildRequest,
    GameModuleFactory,
    ServiceBinder,
    ServiceResolver,
    StartupOverrideHook,
    ViewFactory,
)
from engine.api.context import RuntimeContext
from engine.api.events import EventBus
from engine.api.game_module import GameModule
from engine.api.gameplay import UpdateLoop
from engine.api.hosted_runtime import HostedRuntimeConfig
from engine.api.interaction_modes import InteractionModeMachine
from engine.api.logging import EngineLoggingConfig
from engine.api.module_graph import ModuleGraph
from engine.api.screens import ScreenStack
from engine.api.ui_framework import UIFramework
from warships.game.app.controller import GameController
from warships.game.app.engine_adapter import WarshipsAppAdapter
from warships.game.app.engine_game_module import WarshipsGameModule
from warships.game.app.events import ButtonPressed
from warships.game.app.services.session_flow import default_session_transitions
from warships.game.infra.app_data import resolve_presets_dir
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService
from warships.game.ui.game_view import GameView


class WarshipsModule(EngineModule):
    """Game module declaration consumed by engine runtime entrypoint."""

    def configure(self, binder: ServiceBinder) -> None:
        binder.bind_factory(ControllerFactory, self._build_controller)
        binder.bind_factory(AppAdapterFactory, self._build_app_adapter_factory)
        binder.bind_factory(ViewFactory, self._build_view_factory)
        binder.bind_factory(GameModuleFactory, self._build_game_module_factory)
        binder.bind_factory(StartupOverrideHook, self._build_startup_override_hook)

    def runtime_config(self) -> HostedRuntimeConfig:
        runtime_name = os.getenv("WARSHIPS_GAME_NAME", "warships").strip() or "warships"
        return HostedRuntimeConfig(
            window_mode=os.getenv("ENGINE_WINDOW_MODE", "windowed"),
            runtime_name=runtime_name,
        )

    def logging_config(self) -> EngineLoggingConfig:
        from warships.game.infra.logging import build_logging_config

        return build_logging_config()

    def _build_controller(self, resolver: ServiceResolver) -> ControllerFactory:
        return lambda local_resolver: self._create_controller(local_resolver)

    def _create_controller(self, resolver: ServiceResolver) -> GameController:
        configured_presets = os.getenv("WARSHIPS_PRESETS_DIR", "").strip()
        preset_root = Path(configured_presets) if configured_presets else resolve_presets_dir()
        preset_service = PresetService(PresetRepository(preset_root))
        debug_ui = os.getenv("WARSHIPS_DEBUG_UI", "0") == "1"
        screen_stack: ScreenStack = resolver.resolve(ScreenStack)
        interaction_modes: InteractionModeMachine = resolver.resolve(InteractionModeMachine)
        dispatcher_factory: ActionDispatcherFactory = resolver.resolve(ActionDispatcherFactory)
        flow_program_factory: FlowProgramFactory = resolver.resolve(FlowProgramFactory)
        session_flow_program = flow_program_factory(default_session_transitions())
        return GameController(
            preset_service=preset_service,
            rng=random.Random(),
            screen_stack=screen_stack,
            interaction_modes=interaction_modes,
            action_dispatcher_factory=dispatcher_factory,
            session_flow_program=session_flow_program,
            debug_ui=debug_ui,
        )

    def _build_startup_override_hook(self, resolver: ServiceResolver) -> StartupOverrideHook:
        _ = resolver
        return lambda controller: _apply_startup_screen_override(cast(GameController, controller))

    def _build_app_adapter_factory(self, resolver: ServiceResolver) -> AppAdapterFactory:
        _ = resolver
        return lambda controller: WarshipsAppAdapter(cast(GameController, controller))

    def _build_view_factory(self, resolver: ServiceResolver) -> ViewFactory:
        _ = resolver
        return lambda renderer, layout: GameView(renderer, layout)

    def _build_game_module_factory(self, resolver: ServiceResolver) -> GameModuleFactory:
        runtime_context: RuntimeContext = resolver.resolve(RuntimeContext)
        event_bus: EventBus = resolver.resolve(EventBus)
        update_loop: UpdateLoop = resolver.resolve(UpdateLoop)
        module_graph: ModuleGraph = resolver.resolve(ModuleGraph)

        def _factory(
            request: GameModuleBuildRequest,
        ) -> GameModule:
            return WarshipsGameModule(
                controller=cast(GameController, request.controller),
                framework=cast(UIFramework, request.framework),
                view=cast(GameView, request.view),
                debug_ui=request.debug_ui,
                event_bus=event_bus,
                runtime_context=runtime_context,
                update_loop=update_loop,
                module_graph=module_graph,
            )

        return _factory


def _apply_startup_screen_override(controller: GameController) -> None:
    """Allow deterministic startup directly into a target screen for profiling."""
    target = os.getenv("WARSHIPS_START_SCREEN", "").strip().lower()
    if not target or target == "main_menu":
        return
    if target == "new_game_setup":
        controller.handle_button(ButtonPressed("new_game"))
        return
    if target == "preset_manage":
        controller.handle_button(ButtonPressed("manage_presets"))
        return
    if target == "placement_edit":
        controller.handle_button(ButtonPressed("manage_presets"))
        rows = controller.ui_state().preset_rows
        if rows:
            controller.handle_button(ButtonPressed(f"preset_edit:{rows[0].name}"))
            return
        controller.handle_button(ButtonPressed("create_preset"))
        return
    if target == "battle":
        controller.handle_button(ButtonPressed("new_game"))
        controller.handle_button(ButtonPressed("new_game_randomize"))
        controller.handle_button(ButtonPressed("start_game"))

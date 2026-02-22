"""Runtime-owned public entrypoint for game module execution."""

from __future__ import annotations

from engine.api.composition import (
    AppAdapterFactory,
    ControllerPort,
    ControllerFactory,
    EngineModule,
    GameModuleBuildRequest,
    GameModuleFactory,
    StartupOverrideHook,
    ViewFactory,
)
from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.api.ui_primitives import GridLayout
from engine.runtime.bootstrap import run_hosted_runtime
from engine.runtime.composition_container import RuntimeCompositionContainer
from engine.runtime.framework_engine import EngineUIFramework
from engine.runtime.host import EngineHostConfig
from engine.runtime.logging import configure_engine_logging
from engine.runtime.ui_space import create_app_render_api
from engine.sdk.catalog import bind_sdk_defaults


def run(*, module: EngineModule) -> None:
    """Run one game module using engine-owned hosted runtime composition."""
    container = RuntimeCompositionContainer()
    bind_sdk_defaults(container)
    module.configure(container)

    config = module.runtime_config()
    configure_engine_logging(module.logging_config())
    host_config = EngineHostConfig(
        window_mode=str(config.window_mode),
        width=int(config.width),
        height=int(config.height),
        runtime_name=str(config.runtime_name),
    )
    debug_ui = bool(config.debug_ui)
    controller_factory: ControllerFactory = container.resolve(ControllerFactory)
    app_adapter_factory: AppAdapterFactory = container.resolve(AppAdapterFactory)
    view_factory: ViewFactory = container.resolve(ViewFactory)
    game_module_factory: GameModuleFactory = container.resolve(GameModuleFactory)
    startup_hook: StartupOverrideHook = container.resolve(StartupOverrideHook)

    controller: ControllerPort = controller_factory(container)
    startup_hook(controller)

    def _module_factory(renderer: RenderAPI, layout: GridLayout) -> GameModule:
        app = app_adapter_factory(controller)
        app_renderer = create_app_render_api(app=app, renderer=renderer)
        view = view_factory(app_renderer, layout)
        framework = EngineUIFramework(
            app=app,
            renderer=renderer,
            layout=layout,
        )
        return game_module_factory(
            GameModuleBuildRequest(
                controller=controller,
                framework=framework,
                view=view,
                debug_ui=debug_ui,
                resolver=container,
            )
        )

    run_hosted_runtime(
        module_factory=_module_factory,
        host_config=host_config,
    )

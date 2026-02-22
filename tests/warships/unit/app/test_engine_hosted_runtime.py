from __future__ import annotations

from engine.api.composition import (
    AppAdapterFactory,
    ControllerFactory,
    GameModuleFactory,
    StartupOverrideHook,
    ViewFactory,
)
from engine.runtime.composition_container import RuntimeCompositionContainer
from engine.sdk.catalog import bind_sdk_defaults
import warships.game.app.engine_hosted_runtime as runtime_mod


def test_warships_module_exposes_runtime_config_and_bindings() -> None:
    module = runtime_mod.WarshipsModule()
    config = module.runtime_config()
    assert config.window_mode in {"windowed", "maximized", "fullscreen", "borderless"}
    container = RuntimeCompositionContainer()
    bind_sdk_defaults(container)
    module.configure(container)

    controller_factory = container.resolve(ControllerFactory)
    controller = controller_factory(container)
    assert controller is not None

    assert container.resolve(AppAdapterFactory) is not None
    assert container.resolve(ViewFactory) is not None
    assert container.resolve(GameModuleFactory) is not None
    assert container.resolve(StartupOverrideHook) is not None

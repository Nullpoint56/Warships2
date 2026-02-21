"""Public engine-hosted runtime bootstrap API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from engine.api.game_module import GameModule
from engine.api.render import RenderAPI
from engine.api.ui_primitives import GridLayout


@dataclass(frozen=True, slots=True)
class HostedRuntimeConfig:
    """Public runtime configuration for hosted execution."""

    window_mode: str = "windowed"
    width: int = 1280
    height: int = 800
    runtime_name: str = "game"


def run_hosted_runtime(
    *,
    module_factory: Callable[[RenderAPI, GridLayout], GameModule],
    host_config: HostedRuntimeConfig | None = None,
) -> None:
    """Run hosted runtime using default engine implementation."""
    from engine.runtime.bootstrap import run_hosted_runtime as _run
    from engine.runtime.host import EngineHostConfig

    config = host_config or HostedRuntimeConfig()
    _run(
        module_factory=module_factory,
        host_config=EngineHostConfig(
            window_mode=config.window_mode,
            width=config.width,
            height=config.height,
            runtime_name=config.runtime_name,
        ),
    )

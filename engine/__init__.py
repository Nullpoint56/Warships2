"""Engine runtime and API boundary modules."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.api.composition import EngineModule


def run(*, module: "EngineModule") -> None:
    """Run one game module with runtime-owned composition."""
    from engine.runtime.entrypoint import run as runtime_run

    runtime_run(module=module)

__all__ = ["run"]

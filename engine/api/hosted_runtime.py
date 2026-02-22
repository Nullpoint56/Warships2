"""Public hosted runtime configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HostedRuntimeConfig:
    """Public runtime configuration for hosted execution."""

    window_mode: str = "windowed"
    width: int = 1280
    height: int = 800
    runtime_name: str = "game"
    debug_ui: bool = False

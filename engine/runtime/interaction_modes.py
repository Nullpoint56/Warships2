"""Interaction mode machine and routing gates."""

from __future__ import annotations

from engine.api.interaction_modes import InteractionMode


class RuntimeInteractionModeMachine:
    """Runtime mode switch for input gating."""

    def __init__(self) -> None:
        self._modes: dict[str, InteractionMode] = {}
        self.register(InteractionMode("default", True, True, True))
        self.register(InteractionMode("modal", True, True, False))
        self.register(InteractionMode("captured", True, True, True))
        self._current = "default"

    @property
    def current_mode(self) -> str:
        return self._current

    def register(self, mode: InteractionMode) -> None:
        """Register or replace a mode definition."""
        normalized = mode.name.strip().lower()
        if not normalized:
            raise ValueError("mode name must not be empty")
        self._modes[normalized] = InteractionMode(
            name=normalized,
            allow_pointer=mode.allow_pointer,
            allow_keyboard=mode.allow_keyboard,
            allow_wheel=mode.allow_wheel,
        )

    def set_mode(self, mode_name: str) -> None:
        """Switch to a registered mode."""
        normalized = mode_name.strip().lower()
        if normalized not in self._modes:
            raise KeyError(f"unknown mode: {mode_name}")
        self._current = normalized

    def allows_pointer(self) -> bool:
        return self._active().allow_pointer

    def allows_keyboard(self) -> bool:
        return self._active().allow_keyboard

    def allows_wheel(self) -> bool:
        return self._active().allow_wheel

    def _active(self) -> InteractionMode:
        return self._modes[self._current]


InteractionModeMachine = RuntimeInteractionModeMachine

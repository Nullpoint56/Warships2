"""Generic action-dispatch helpers for runtime/controller orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from engine.api.action_dispatch import DirectActionHandler, PrefixedActionHandler


@dataclass(frozen=True, slots=True)
class RuntimeActionDispatcher:
    """Resolve and dispatch action ids by direct match or prefix handlers."""

    direct_handlers: dict[str, DirectActionHandler]
    prefixed_handlers: tuple[tuple[str, PrefixedActionHandler], ...]

    def dispatch(self, action_id: str) -> bool | None:
        """Dispatch action id. Return None when no handler exists."""
        handler = self.direct_handlers.get(action_id)
        if handler is not None:
            return handler()
        for prefix, prefixed_handler in self.prefixed_handlers:
            if action_id.startswith(prefix):
                # Prefix handlers receive the dynamic suffix after their registered prefix.
                suffix = action_id[len(prefix) :]
                return prefixed_handler(suffix)
        return None


ActionDispatcher = RuntimeActionDispatcher

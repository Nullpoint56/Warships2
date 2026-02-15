"""Shared list-scroll semantics for UI menus."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScrollOutcome:
    """Result of a wheel scroll attempt."""

    handled: bool
    next_scroll: int


class MenuScrollService:
    """Wheel delta to list-scroll conversion."""

    @staticmethod
    def apply(dy: float, current_scroll: int, can_scroll_down: bool) -> ScrollOutcome:
        if dy < 0 and current_scroll > 0:
            return ScrollOutcome(handled=True, next_scroll=current_scroll - 1)
        if dy > 0 and can_scroll_down:
            return ScrollOutcome(handled=True, next_scroll=current_scroll + 1)
        return ScrollOutcome(handled=False, next_scroll=current_scroll)


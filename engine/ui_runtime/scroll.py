"""Generic list scrolling helpers for wheel input semantics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScrollOutcome:
    """Result of attempting to scroll a list-like viewport."""

    handled: bool
    next_scroll: int


def apply_wheel_scroll(dy: float, current_scroll: int, can_scroll_down: bool) -> ScrollOutcome:
    """Convert wheel delta into list scroll index changes."""
    if dy < 0 and current_scroll > 0:
        return ScrollOutcome(handled=True, next_scroll=current_scroll - 1)
    if dy > 0 and can_scroll_down:
        return ScrollOutcome(handled=True, next_scroll=current_scroll + 1)
    return ScrollOutcome(handled=False, next_scroll=current_scroll)

"""Generic list-viewport helpers for scrollable UI projections."""

from __future__ import annotations

from collections.abc import Sequence


def visible_slice[T](items: Sequence[T], scroll: int, visible_count: int) -> list[T]:
    """Return visible window slice for a list viewport."""
    normalized_visible = max(0, visible_count)
    clamped_scroll = clamp_scroll(scroll, normalized_visible, len(items))
    return list(items[clamped_scroll : clamped_scroll + normalized_visible])


def can_scroll_down(scroll: int, visible_count: int, total_count: int) -> bool:
    """Return whether there are items below the current viewport."""
    normalized_visible = max(0, visible_count)
    clamped_scroll = clamp_scroll(scroll, normalized_visible, total_count)
    return clamped_scroll + normalized_visible < max(0, total_count)


def clamp_scroll(scroll: int, visible_count: int, total_count: int) -> int:
    """Clamp scroll offset to valid list viewport bounds."""
    normalized_visible = max(0, visible_count)
    max_scroll = max(0, total_count - normalized_visible)
    return max(0, min(scroll, max_scroll))

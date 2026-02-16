"""Generic list-viewport helpers for scrollable UI projections."""

from __future__ import annotations

from typing import TypeVar


T = TypeVar("T")


def visible_slice(items: list[T], scroll: int, visible_count: int) -> list[T]:
    """Return visible window slice for a list viewport."""
    return list(items[scroll : scroll + visible_count])


def can_scroll_down(scroll: int, visible_count: int, total_count: int) -> bool:
    """Return whether there are items below the current viewport."""
    return scroll + visible_count < total_count


def clamp_scroll(scroll: int, visible_count: int, total_count: int) -> int:
    """Clamp scroll offset to valid list viewport bounds."""
    max_scroll = max(0, total_count - visible_count)
    return max(0, min(scroll, max_scroll))

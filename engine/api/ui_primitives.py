"""Public UI primitive contracts and thin runtime helper facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from engine.ui_runtime import geometry as _geo
from engine.ui_runtime import grid_layout as _grid
from engine.ui_runtime import interactions as _interactions
from engine.ui_runtime import keymap as _keymap
from engine.ui_runtime import list_viewport as _list_viewport
from engine.ui_runtime import modal_runtime as _modal
from engine.ui_runtime import prompt_runtime as _prompt
from engine.ui_runtime import scroll as _scroll

CellCoord = _geo.CellCoord
Rect = _geo.Rect
GridLayout = _grid.GridLayout
NonModalKeyRoute = _interactions.NonModalKeyRoute
can_scroll_with_wheel = _interactions.can_scroll_with_wheel
resolve_pointer_button = _interactions.resolve_pointer_button
route_non_modal_key_event = _interactions.route_non_modal_key_event
map_key_name = _keymap.map_key_name
can_scroll_list_down = _list_viewport.can_scroll_down
clamp_scroll = _list_viewport.clamp_scroll
visible_slice = _list_viewport.visible_slice
ModalInputState = _modal.ModalInputState
ModalKeyRoute = _modal.ModalKeyRoute
ModalPointerRoute = _modal.ModalPointerRoute
route_modal_key_event = _modal.route_modal_key_event
route_modal_pointer_event = _modal.route_modal_pointer_event
PromptInteractionOutcome = _prompt.PromptInteractionOutcome
PromptState = _prompt.PromptState
PromptView = _prompt.PromptView
close_prompt = _prompt.close_prompt
open_prompt = _prompt.open_prompt
sync_prompt = _prompt.sync_prompt
handle_prompt_button = _prompt.handle_button
handle_prompt_char = _prompt.handle_char
handle_prompt_key = _prompt.handle_key
ScrollOutcome = _scroll.ScrollOutcome
apply_wheel_scroll = _scroll.apply_wheel_scroll

type TextOverflowPolicy = Literal["clip", "ellipsis", "wrap-none"]


@dataclass(frozen=True, slots=True)
class ButtonStyle:
    """Optional per-button style overrides supplied by app-side code."""

    bg_color: str | None = None
    border_color: str | None = None
    highlight_color: str | None = None
    text_color: str | None = None
    radius: float | None = None
    border_thickness: float | None = None
    glossy: bool | None = None
    highlight_height_ratio: float | None = None
    shadow_enabled: bool | None = None
    shadow_color: str | None = None
    shadow_layers: int | None = None
    shadow_spread: float | None = None
    shadow_offset_x: float | None = None
    shadow_offset_y: float | None = None


@dataclass(frozen=True, slots=True)
class Button:
    """Clickable rectangular button primitive."""

    id: str
    x: float
    y: float
    w: float
    h: float
    visible: bool = True
    enabled: bool = True
    style: ButtonStyle | dict[str, object] | None = None

    def contains(self, px: float, py: float) -> bool:
        """Return whether this button contains the point."""
        return self.visible and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


def truncate_text(text: str, max_len: int) -> str:
    """Truncate label text to max length using ellipsis when possible."""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def clip_text(text: str, max_len: int) -> str:
    """Clip text to max length without ellipsis."""
    return str(text)[: max(0, int(max_len))]


def apply_text_overflow(text: str, max_len: int, policy: TextOverflowPolicy) -> str:
    """Apply overflow policy to one-line text."""
    normalized = str(text)
    max_chars = max(0, int(max_len))
    if len(normalized) <= max_chars:
        return normalized
    if policy == "clip":
        return clip_text(normalized, max_chars)
    if policy == "wrap-none":
        return normalized
    return truncate_text(normalized, max_chars)


def fit_text_to_rect(
    text: str,
    *,
    rect_w: float,
    rect_h: float,
    base_font_size: float,
    min_font_size: float = 8.0,
    pad_x: float = 10.0,
    pad_y: float = 6.0,
    overflow_policy: TextOverflowPolicy = "ellipsis",
) -> tuple[str, float]:
    """Fit one-line text by shrinking first; apply overflow only at minimum size."""
    normalized = str(text)
    if not normalized:
        return "", float(base_font_size)
    avail_w = max(1.0, float(rect_w) - (2.0 * float(pad_x)))
    avail_h = max(1.0, float(rect_h) - (2.0 * float(pad_y)))
    min_size = max(1.0, float(min_font_size))
    size = max(min_size, float(base_font_size))
    est_char_w_factor = 0.62
    est_line_h_factor = 1.25
    while size >= min_size:
        est_line_h = float(size) * est_line_h_factor
        if est_line_h > avail_h:
            size -= 1.0
            continue
        est_char_w = max(1.0, float(size) * est_char_w_factor)
        max_chars = int(avail_w // est_char_w)
        if max_chars >= len(normalized):
            return normalized, float(size)
        if max_chars > 0:
            if overflow_policy == "wrap-none":
                if len(normalized) <= max_chars:
                    return normalized, float(size)
            elif size <= min_size:
                return apply_text_overflow(normalized, max_chars, overflow_policy), float(size)
        size -= 1.0
    return apply_text_overflow(normalized, 1, overflow_policy), float(min_size)


def clamp_child_rect_to_parent(
    child: Rect,
    parent: Rect,
    *,
    pad_x: float = 0.0,
    pad_y: float = 0.0,
) -> Rect:
    """Clamp child rectangle to fit inside parent content box."""
    content_x = float(parent.x) + max(0.0, float(pad_x))
    content_y = float(parent.y) + max(0.0, float(pad_y))
    content_w = max(0.0, float(parent.w) - (2.0 * max(0.0, float(pad_x))))
    content_h = max(0.0, float(parent.h) - (2.0 * max(0.0, float(pad_y))))
    child_w = min(max(0.0, float(child.w)), content_w)
    child_h = min(max(0.0, float(child.h)), content_h)
    max_x = content_x + content_w - child_w
    max_y = content_y + content_h - child_h
    child_x = min(max(float(child.x), content_x), max_x)
    child_y = min(max(float(child.y), content_y), max_y)
    return Rect(child_x, child_y, child_w, child_h)


def parent_rect_from_children(
    children: tuple[Rect, ...] | list[Rect],
    *,
    pad_x: float = 0.0,
    pad_y: float = 0.0,
    min_w: float = 0.0,
    min_h: float = 0.0,
) -> Rect:
    """Compute parent bounds that fit all child rects plus optional padding."""
    if not children:
        return Rect(0.0, 0.0, max(0.0, float(min_w)), max(0.0, float(min_h)))
    left = min(float(child.x) for child in children)
    top = min(float(child.y) for child in children)
    right = max(float(child.x) + float(child.w) for child in children)
    bottom = max(float(child.y) + float(child.h) for child in children)
    px = max(0.0, float(pad_x))
    py = max(0.0, float(pad_y))
    x = left - px
    y = top - py
    w = max(float(min_w), (right - left) + (2.0 * px))
    h = max(float(min_h), (bottom - top) + (2.0 * py))
    return Rect(x, y, w, h)


__all__ = [
    "Button",
    "ButtonStyle",
    "CellCoord",
    "GridLayout",
    "ModalInputState",
    "ModalKeyRoute",
    "ModalPointerRoute",
    "NonModalKeyRoute",
    "PromptInteractionOutcome",
    "PromptState",
    "PromptView",
    "Rect",
    "ScrollOutcome",
    "TextOverflowPolicy",
    "apply_text_overflow",
    "apply_wheel_scroll",
    "can_scroll_list_down",
    "can_scroll_with_wheel",
    "clip_text",
    "clamp_child_rect_to_parent",
    "clamp_scroll",
    "close_prompt",
    "fit_text_to_rect",
    "handle_prompt_button",
    "handle_prompt_char",
    "handle_prompt_key",
    "map_key_name",
    "open_prompt",
    "parent_rect_from_children",
    "resolve_pointer_button",
    "route_modal_key_event",
    "route_modal_pointer_event",
    "route_non_modal_key_event",
    "sync_prompt",
    "truncate_text",
    "visible_slice",
]

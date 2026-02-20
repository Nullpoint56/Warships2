"""Public UI primitive types and helper functions."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from engine.api.app_port import InteractionPlanView, ModalWidgetView


@dataclass(frozen=True, slots=True)
class Rect:
    """Simple axis-aligned rectangle."""

    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        """Return whether a point is inside the rectangle."""
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True, slots=True)
class CellCoord:
    """Grid cell coordinate in row/column space."""

    row: int
    col: int


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

    def contains(self, px: float, py: float) -> bool:
        """Return whether this button contains the point."""
        return self.visible and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True, slots=True)
class GridLayout:
    """Layout and hit-testing helpers for a two-surface cell grid."""

    primary_origin_x: float = 80.0
    secondary_origin_x: float = 640.0
    origin_y: float = 150.0
    cell_size: float = 42.0
    grid_size: int = 10

    def _origin_x_for_target(self, grid_target: str) -> float:
        normalized = grid_target.strip().lower()
        if normalized == "secondary":
            return self.secondary_origin_x
        if normalized == "primary":
            return self.primary_origin_x
        raise ValueError(f"unknown grid target: {grid_target!r}")

    def rect_for_target(self, grid_target: str) -> Rect:
        """Return rectangle for a named grid target."""
        size_px = self.grid_size * self.cell_size
        return Rect(self._origin_x_for_target(grid_target), self.origin_y, size_px, size_px)

    def cell_rect_for_target(self, grid_target: str, row: int, col: int) -> Rect:
        """Return pixel rectangle for a grid cell."""
        origin_x = self._origin_x_for_target(grid_target)
        return Rect(
            x=origin_x + col * self.cell_size,
            y=self.origin_y + row * self.cell_size,
            w=self.cell_size,
            h=self.cell_size,
        )

    def screen_to_cell(self, grid_target: str, px: float, py: float) -> CellCoord | None:
        """Convert screen point to cell coordinate for a named grid target."""
        rect = self.rect_for_target(grid_target)
        if not rect.contains(px, py):
            return None
        col = int((px - rect.x) // self.cell_size)
        row = int((py - rect.y) // self.cell_size)
        if not (0 <= row < self.grid_size and 0 <= col < self.grid_size):
            return None
        return CellCoord(row=row, col=col)


@dataclass(frozen=True, slots=True)
class PromptView:
    """Prompt view-model with title/value and action button ids."""

    title: str
    value: str
    confirm_button_id: str
    cancel_button_id: str


@dataclass(frozen=True, slots=True)
class PromptState:
    """Current prompt input runtime state."""

    prompt: PromptView | None = None
    buffer: str = ""
    mode: str | None = None
    target: str | None = None


@dataclass(frozen=True, slots=True)
class PromptInteractionOutcome:
    """Outcome of prompt input routing before app-specific confirmation logic."""

    handled: bool
    state: PromptState
    request_confirm: bool = False
    refresh_buttons: bool = False


@dataclass(frozen=True, slots=True)
class ScrollOutcome:
    """Result of attempting to scroll a list-like viewport."""

    handled: bool
    next_scroll: int


@dataclass(slots=True)
class ModalInputState:
    """Tracks modal lifecycle and text-input focus state."""

    is_open: bool = False
    input_focused: bool = False

    def sync(self, widget: ModalWidgetView | None) -> None:
        """Sync state with current modal presence."""
        if widget is None:
            self.is_open = False
            self.input_focused = False
            return
        if not self.is_open:
            self.input_focused = True
        self.is_open = True


@dataclass(frozen=True, slots=True)
class ModalPointerRoute:
    """Routing result for a pointer event while modal is open."""

    swallow: bool
    button_id: str | None = None
    focus_input: bool | None = None


@dataclass(frozen=True, slots=True)
class ModalKeyRoute:
    """Routing result for a key/char event while modal is open."""

    swallow: bool
    key: str | None = None
    char: str | None = None


@dataclass(frozen=True, slots=True)
class NonModalKeyRoute:
    """Routing result for a key/char event when no modal is open."""

    controller_key: str | None = None
    controller_char: str | None = None
    shortcut_button_id: str | None = None


def visible_slice[T](items: Sequence[T], scroll: int, visible_count: int) -> list[T]:
    """Return visible window slice for a list viewport."""
    normalized_visible = max(0, visible_count)
    clamped_scroll = clamp_scroll(scroll, normalized_visible, len(items))
    return list(items[clamped_scroll : clamped_scroll + normalized_visible])


def truncate_text(text: str, max_len: int) -> str:
    """Truncate label text to max length using ellipsis when possible."""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def fit_text_to_rect(
    text: str,
    *,
    rect_w: float,
    rect_h: float,
    base_font_size: float,
    min_font_size: float = 8.0,
    pad_x: float = 10.0,
    pad_y: float = 6.0,
) -> tuple[str, float]:
    """Fit label text inside a rectangle with deterministic engine text metrics."""
    normalized = str(text)
    if not normalized:
        return "", float(base_font_size)
    avail_w = max(1.0, float(rect_w) - (2.0 * float(pad_x)))
    avail_h = max(1.0, float(rect_h) - (2.0 * float(pad_y)))
    min_pixel = max(1, int(round(float(min_font_size) / 8.0)))
    preferred_pixel = max(min_pixel, int(round(float(base_font_size) / 8.0)))
    max_pixel_by_height = max(1, int(avail_h // 7.0))
    pixel = min(preferred_pixel, max_pixel_by_height)
    while pixel >= min_pixel:
        max_chars = int(((avail_w / float(pixel)) + 1.0) // 6.0)
        if max_chars >= len(normalized):
            return normalized, float(pixel * 8)
        if max_chars > 0:
            return truncate_text(normalized, max_chars), float(pixel * 8)
        pixel -= 1
    return truncate_text(normalized, 1), float(min_pixel * 8)


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
    children: Sequence[Rect],
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


def can_scroll_list_down(scroll: int, visible_count: int, total_count: int) -> bool:
    """Return whether there are items below the current viewport."""
    normalized_visible = max(0, visible_count)
    clamped_scroll = clamp_scroll(scroll, normalized_visible, total_count)
    return clamped_scroll + normalized_visible < max(0, total_count)


def clamp_scroll(scroll: int, visible_count: int, total_count: int) -> int:
    """Clamp scroll offset to valid list viewport bounds."""
    normalized_visible = max(0, visible_count)
    max_scroll = max(0, total_count - normalized_visible)
    return max(0, min(scroll, max_scroll))


def open_prompt(
    *,
    title: str,
    initial_value: str,
    confirm_button_id: str,
    cancel_button_id: str = "prompt_cancel",
    mode: str | None = None,
    target: str | None = None,
) -> PromptState:
    """Create prompt state with initial buffer and prompt metadata."""
    return PromptState(
        prompt=PromptView(
            title=title,
            value=initial_value,
            confirm_button_id=confirm_button_id,
            cancel_button_id=cancel_button_id,
        ),
        buffer=initial_value,
        mode=mode,
        target=target,
    )


def close_prompt() -> PromptState:
    """Close prompt and reset prompt input state."""
    return PromptState()


def sync_prompt(state: PromptState, value: str) -> PromptState:
    """Sync prompt buffer and prompt value text."""
    prompt = state.prompt
    if prompt is None:
        return state
    return PromptState(
        prompt=PromptView(
            title=prompt.title,
            value=value,
            confirm_button_id=prompt.confirm_button_id,
            cancel_button_id=prompt.cancel_button_id,
        ),
        buffer=value,
        mode=state.mode,
        target=state.target,
    )


def handle_prompt_button(
    state: PromptState,
    button_id: str,
    *,
    extra_confirm_button_ids: Collection[str] = (),
) -> PromptInteractionOutcome:
    """Handle prompt button actions for cancel/confirm semantics."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if button_id == state.prompt.cancel_button_id:
        return PromptInteractionOutcome(
            handled=True,
            state=close_prompt(),
            refresh_buttons=True,
        )
    if button_id == state.prompt.confirm_button_id or button_id in extra_confirm_button_ids:
        return PromptInteractionOutcome(handled=True, state=state, request_confirm=True)
    return PromptInteractionOutcome(handled=False, state=state)


def handle_prompt_key(state: PromptState, key: str) -> PromptInteractionOutcome:
    """Handle prompt key interactions (backspace/enter/escape)."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if key == "backspace":
        return PromptInteractionOutcome(
            handled=True,
            state=sync_prompt(state, state.buffer[:-1]),
        )
    if key == "enter":
        return PromptInteractionOutcome(handled=True, state=state, request_confirm=True)
    if key == "escape":
        return PromptInteractionOutcome(
            handled=True,
            state=close_prompt(),
            refresh_buttons=True,
        )
    return PromptInteractionOutcome(handled=False, state=state)


def handle_prompt_char(state: PromptState, ch: str, max_len: int = 32) -> PromptInteractionOutcome:
    """Handle prompt text input updates."""
    if state.prompt is None:
        return PromptInteractionOutcome(handled=False, state=state)
    if len(ch) != 1 or not ch.isprintable():
        return PromptInteractionOutcome(handled=False, state=state)
    if len(state.buffer) >= max_len:
        return PromptInteractionOutcome(handled=False, state=state)
    return PromptInteractionOutcome(
        handled=True,
        state=sync_prompt(state, state.buffer + ch),
    )


def apply_wheel_scroll(dy: float, current_scroll: int, can_scroll_down: bool) -> ScrollOutcome:
    """Convert wheel delta into list scroll index changes."""
    if dy < 0 and current_scroll > 0:
        return ScrollOutcome(handled=True, next_scroll=current_scroll - 1)
    if dy > 0 and can_scroll_down:
        return ScrollOutcome(handled=True, next_scroll=current_scroll + 1)
    return ScrollOutcome(handled=False, next_scroll=current_scroll)


def map_key_name(key_name: str) -> str | None:
    """Normalize backend key names to app/controller key identifiers."""
    normalized = key_name.strip().lower()
    key_map = {
        "backspace": "backspace",
        "enter": "enter",
        "return": "enter",
        "escape": "escape",
        "esc": "escape",
        "r": "r",
        "d": "d",
    }
    if normalized in key_map:
        return key_map[normalized]
    if len(normalized) == 1 and normalized.isalpha():
        return normalized
    return None


def resolve_pointer_button(plan: InteractionPlanView, x: float, y: float) -> str | None:
    """Resolve clicked button in interaction plan."""
    for button in plan.buttons:
        if button.enabled and button.contains(x, y):
            return button.id
    return None


def can_scroll_with_wheel(plan: InteractionPlanView, x: float, y: float) -> bool:
    """Return whether wheel should route to app on this point."""
    for region in plan.wheel_scroll_regions:
        if region.contains(x, y):
            return True
    return False


def route_non_modal_key_event(
    event_type: str,
    value: str,
    plan: InteractionPlanView,
) -> NonModalKeyRoute:
    """Route key event when no modal is active."""
    if event_type == "char":
        if len(value) != 1 or not value.isprintable():
            return NonModalKeyRoute()
        return NonModalKeyRoute(controller_char=value)
    if event_type != "key_down":
        return NonModalKeyRoute()
    mapped = map_key_name(value)
    if mapped is None:
        return NonModalKeyRoute()
    return NonModalKeyRoute(
        controller_key=mapped,
        shortcut_button_id=plan.shortcut_buttons.get(mapped),
    )


def route_modal_pointer_event(
    widget: ModalWidgetView,
    state: ModalInputState,
    x: float,
    y: float,
    button: int,
) -> ModalPointerRoute:
    """Route a pointer-down event when a modal is active."""
    if button != 1:
        return ModalPointerRoute(swallow=True)
    target = _resolve_modal_pointer_target(widget, x, y)
    if target == "confirm":
        return ModalPointerRoute(swallow=True, button_id=widget.confirm_button_id)
    if target == "cancel":
        return ModalPointerRoute(swallow=True, button_id=widget.cancel_button_id)
    if target == "input":
        return ModalPointerRoute(swallow=True, focus_input=True)
    if target in {"panel", "overlay"}:
        return ModalPointerRoute(swallow=True, focus_input=False)
    return ModalPointerRoute(swallow=True, focus_input=state.input_focused)


def route_modal_key_event(
    event_type: str,
    value: str,
    mapped_key: str | None,
    state: ModalInputState,
) -> ModalKeyRoute:
    """Route key/char events when a modal is active."""
    if event_type == "char":
        if not state.input_focused:
            return ModalKeyRoute(swallow=True)
        if len(value) != 1 or not value.isprintable():
            return ModalKeyRoute(swallow=True)
        return ModalKeyRoute(swallow=True, char=value)
    if event_type != "key_down":
        return ModalKeyRoute(swallow=True)
    if mapped_key is None:
        return ModalKeyRoute(swallow=True)
    if mapped_key in {"enter", "escape"}:
        return ModalKeyRoute(swallow=True, key=mapped_key)
    if mapped_key == "backspace":
        if not state.input_focused:
            return ModalKeyRoute(swallow=True)
        return ModalKeyRoute(swallow=True, key=mapped_key)
    return ModalKeyRoute(swallow=True)


def _resolve_modal_pointer_target(widget: ModalWidgetView, x: float, y: float) -> str | None:
    if widget.confirm_button_rect.contains(x, y):
        return "confirm"
    if widget.cancel_button_rect.contains(x, y):
        return "cancel"
    if widget.input_rect.contains(x, y):
        return "input"
    if widget.panel_rect.contains(x, y):
        return "panel"
    if widget.overlay_rect.contains(x, y):
        return "overlay"
    return None


__all__ = [
    "Button",
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
    "apply_wheel_scroll",
    "can_scroll_list_down",
    "can_scroll_with_wheel",
    "clamp_child_rect_to_parent",
    "clamp_scroll",
    "close_prompt",
    "fit_text_to_rect",
    "handle_prompt_button",
    "handle_prompt_char",
    "handle_prompt_key",
    "map_key_name",
    "open_prompt",
    "resolve_pointer_button",
    "route_modal_key_event",
    "route_modal_pointer_event",
    "route_non_modal_key_event",
    "sync_prompt",
    "parent_rect_from_children",
    "truncate_text",
    "visible_slice",
]

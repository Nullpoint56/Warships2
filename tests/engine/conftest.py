from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True, slots=True)
class FakeButton:
    id: str
    enabled: bool
    rect: Box

    def contains(self, px: float, py: float) -> bool:
        return self.rect.contains(px, py)


@dataclass(frozen=True, slots=True)
class FakeInteractionPlan:
    buttons: tuple[FakeButton, ...] = ()
    shortcut_buttons: dict[str, str] = field(default_factory=dict)
    cell_click_surface: str | None = None
    wheel_scroll_regions: tuple[Box, ...] = ()


@dataclass(frozen=True, slots=True)
class FakeModalWidget:
    confirm_button_id: str = "prompt_confirm"
    cancel_button_id: str = "prompt_cancel"
    confirm_button_rect: Box = Box(10, 10, 20, 20)
    cancel_button_rect: Box = Box(40, 10, 20, 20)
    input_rect: Box = Box(10, 40, 80, 20)
    panel_rect: Box = Box(0, 0, 100, 100)
    overlay_rect: Box = Box(-50, -50, 200, 200)


class FakeRenderer:
    def __init__(self, scale: float = 1.0) -> None:
        self.scale = scale

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale, y * self.scale


class FakeApp:
    def __init__(self) -> None:
        self._modal: FakeModalWidget | None = None
        self._plan = FakeInteractionPlan()
        self.calls: list[tuple[str, tuple]] = []
        self.on_key_result = True
        self.on_button_result = True
        self.on_wheel_result = True
        self.on_pointer_down_result = True
        self.on_cell_click_result = True

    def set_modal(self, modal: FakeModalWidget | None) -> None:
        self._modal = modal

    def set_plan(self, plan: FakeInteractionPlan) -> None:
        self._plan = plan

    def ui_state(self) -> object:
        return object()

    def modal_widget(self) -> FakeModalWidget | None:
        return self._modal

    def interaction_plan(self) -> FakeInteractionPlan:
        return self._plan

    def on_button(self, button_id: str) -> bool:
        self.calls.append(("on_button", (button_id,)))
        return self.on_button_result

    def on_cell_click(self, surface_target: str, row: int, col: int) -> bool:
        self.calls.append(("on_cell_click", (surface_target, row, col)))
        return self.on_cell_click_result

    def on_pointer_move(self, x: float, y: float) -> bool:
        self.calls.append(("on_pointer_move", (x, y)))
        return True

    def on_pointer_release(self, x: float, y: float, button: int) -> bool:
        self.calls.append(("on_pointer_release", (x, y, button)))
        return True

    def on_pointer_down(self, x: float, y: float, button: int) -> bool:
        self.calls.append(("on_pointer_down", (x, y, button)))
        return self.on_pointer_down_result

    def on_key(self, key: str) -> bool:
        self.calls.append(("on_key", (key,)))
        return self.on_key_result

    def on_char(self, value: str) -> bool:
        self.calls.append(("on_char", (value,)))
        return True

    def on_wheel(self, x: float, y: float, dy: float) -> bool:
        self.calls.append(("on_wheel", (x, y, dy)))
        return self.on_wheel_result

"""Hierarchical design-space layout metrics for rendering and hit-testing."""

from __future__ import annotations

from dataclasses import dataclass

from warships.ui.board_view import Rect


DESIGN_WIDTH = 1200.0
DESIGN_HEIGHT = 720.0


def root_rect() -> Rect:
    """Root background container in design-space."""
    return Rect(0.0, 0.0, DESIGN_WIDTH, DESIGN_HEIGHT)


def top_bar_rect() -> Rect:
    """Top button strip container."""
    return Rect(60.0, 20.0, DESIGN_WIDTH - 120.0, 62.0)


def content_rect() -> Rect:
    """Main content container below top strip and above status."""
    return Rect(60.0, 96.0, DESIGN_WIDTH - 120.0, DESIGN_HEIGHT - 96.0 - 70.0)


def status_rect() -> Rect:
    """Bottom hint/status container."""
    return Rect(60.0, DESIGN_HEIGHT - 70.0, DESIGN_WIDTH - 120.0, 44.0)


def _inset(rect: Rect, dx: float, dy: float) -> Rect:
    return Rect(rect.x + dx, rect.y + dy, max(0.0, rect.w - 2.0 * dx), max(0.0, rect.h - 2.0 * dy))


@dataclass(frozen=True, slots=True)
class PlacementPanelLayout:
    """Placement palette container and child rows."""

    panel_w: float = 90.0
    panel_h: float = 420.0
    right_pad: float = 30.0
    top: float = 150.0
    row_start_y: float = 55.0
    row_step_y: float = 70.0
    row_h: float = 24.0
    row_pad_x: float = 10.0

    def panel_rect(self) -> Rect:
        root = root_rect()
        x = root.x + root.w - self.right_pad - self.panel_w
        return Rect(x, self.top, self.panel_w, self.panel_h)

    def row_rect(self, index: int) -> Rect:
        panel = self.panel_rect()
        row_y = panel.y + self.row_start_y + index * self.row_step_y
        return Rect(panel.x + self.row_pad_x, row_y, panel.w - 2.0 * self.row_pad_x, self.row_h)


@dataclass(frozen=True, slots=True)
class PresetPanelLayout:
    """Preset list container and per-row geometry."""

    panel_pad_x: float = 20.0
    panel_pad_y: float = 4.0
    row_start_y: float = 60.0
    row_h: float = 96.0
    row_step_y: float = 112.0
    row_pad_x: float = 14.0
    button_w: float = 78.0
    button_h: float = 32.0
    button_gap: float = 10.0
    row_button_right_pad: float = 14.0
    preview_cell: float = 5.2
    preview_x_pad: float = 14.0
    preview_y_offset: float = 38.0
    name_x_pad: float = 14.0
    name_y_pad: float = 10.0
    name_max_len: int = 28

    def panel_rect(self) -> Rect:
        return _inset(content_rect(), self.panel_pad_x, self.panel_pad_y)

    def row_rect(self, index: int) -> Rect:
        panel = self.panel_rect()
        row_x = panel.x + self.row_pad_x
        row_y = panel.y + self.row_start_y + index * self.row_step_y
        row_w = panel.w - 2.0 * self.row_pad_x
        return Rect(row_x, row_y, row_w, self.row_h)

    def preview_rect(self, index: int) -> Rect:
        row = self.row_rect(index)
        size = self.preview_cell * 10.0
        return Rect(row.x + self.preview_x_pad, row.y + self.preview_y_offset, size, size)

    def action_button_rects(self, index: int) -> tuple[Rect, Rect, Rect]:
        row = self.row_rect(index)
        buttons_w = 3.0 * self.button_w + 2.0 * self.button_gap
        left_x = row.x + row.w - buttons_w - self.row_button_right_pad
        y = row.y + 48.0
        return (
            Rect(left_x, y, self.button_w, self.button_h),
            Rect(left_x + self.button_w + self.button_gap, y, self.button_w, self.button_h),
            Rect(left_x + 2.0 * (self.button_w + self.button_gap), y, self.button_w, self.button_h),
        )


@dataclass(frozen=True, slots=True)
class PromptLayout:
    """Modal prompt layout derived from root box."""

    panel_w: float = 500.0
    panel_h: float = 220.0
    input_h: float = 44.0
    button_w: float = 120.0
    button_h: float = 46.0
    button_gap: float = 20.0

    def overlay_rect(self) -> Rect:
        return root_rect()

    def panel_rect(self) -> Rect:
        root = root_rect()
        x = root.x + (root.w - self.panel_w) / 2.0
        y = root.y + (root.h - self.panel_h) / 2.0
        return Rect(x, y, self.panel_w, self.panel_h)

    def input_rect(self) -> Rect:
        panel = self.panel_rect()
        return Rect(panel.x + 30.0, panel.y + 80.0, panel.w - 60.0, self.input_h)

    def confirm_button_rect(self) -> Rect:
        panel = self.panel_rect()
        total_w = 2.0 * self.button_w + self.button_gap
        left_x = panel.x + (panel.w - total_w) / 2.0
        return Rect(left_x, panel.y + panel.h - 70.0, self.button_w, self.button_h)

    def cancel_button_rect(self) -> Rect:
        first = self.confirm_button_rect()
        return Rect(first.x + self.button_w + self.button_gap, first.y, self.button_w, self.button_h)


PLACEMENT_PANEL = PlacementPanelLayout()
PRESET_PANEL = PresetPanelLayout()
PROMPT = PromptLayout()


@dataclass(frozen=True, slots=True)
class NewGameSetupLayout:
    """New game setup container geometry."""

    panel_pad_x: float = 0.0
    panel_pad_y: float = 0.0
    difficulty_x_pad: float = 20.0
    difficulty_y: float = 70.0
    difficulty_w: float = 260.0
    difficulty_h: float = 42.0
    dropdown_row_h: float = 36.0
    dropdown_gap: float = 4.0
    list_x_pad: float = 20.0
    list_y: float = 250.0
    list_w: float = 420.0
    list_h: float = 250.0
    list_row_h: float = 48.0
    list_row_gap: float = 8.0
    random_btn_y: float = 510.0
    random_btn_w: float = 180.0
    random_btn_h: float = 44.0
    preview_x: float = 520.0
    preview_y: float = 210.0
    preview_cell: float = 18.0

    def panel_rect(self) -> Rect:
        return _inset(content_rect(), self.panel_pad_x, self.panel_pad_y)

    def difficulty_rect(self) -> Rect:
        panel = self.panel_rect()
        return Rect(panel.x + self.difficulty_x_pad, panel.y + self.difficulty_y, self.difficulty_w, self.difficulty_h)

    def difficulty_option_rect(self, index: int) -> Rect:
        base = self.difficulty_rect()
        y = base.y + base.h + 10.0 + index * (self.dropdown_row_h + self.dropdown_gap)
        return Rect(base.x, y, base.w, self.dropdown_row_h)

    def preset_list_rect(self) -> Rect:
        panel = self.panel_rect()
        return Rect(panel.x + self.list_x_pad, panel.y + self.list_y, self.list_w, self.list_h)

    def preset_row_rect(self, visible_index: int) -> Rect:
        list_rect = self.preset_list_rect()
        y = list_rect.y + 14.0 + visible_index * (self.list_row_h + self.list_row_gap)
        return Rect(list_rect.x + 12.0, y, list_rect.w - 24.0, self.list_row_h)

    def random_button_rect(self) -> Rect:
        panel = self.panel_rect()
        return Rect(panel.x + self.list_x_pad, panel.y + self.random_btn_y, self.random_btn_w, self.random_btn_h)

    def preview_origin(self) -> tuple[float, float]:
        panel = self.panel_rect()
        return panel.x + self.preview_x, panel.y + self.preview_y


NEW_GAME_SETUP = NewGameSetupLayout()

"""Retained-mode game rendering for Warships."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from engine.api.render_snapshot import (
    RenderCommand,
    RenderPassSnapshot,
    RenderSnapshot,
    Vec3,
    mat4_translation,
)
from engine.api.render import RenderAPI as Render2D
from engine.api.ui_primitives import Button, GridLayout, fit_text_to_rect
from engine.api.ui_style import (
    DEFAULT_UI_STYLE_TOKENS,
    draw_rounded_rect,
    draw_shadow_rect,
)
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
from warships.game.ui.scene_theme import SceneTheme, theme_for_state
from warships.game.ui.framework.widgets import (
    build_modal_text_input_widget,
    render_modal_text_input_widget,
)
from warships.game.ui.overlays import button_label
from warships.game.ui.views import (
    draw_ai_board,
    draw_new_game_setup,
    draw_placement_panel,
    draw_player_board,
    draw_preset_manage,
    draw_status_bar,
    is_new_game_custom_button,
)

logger = logging.getLogger(__name__)
TOKENS = DEFAULT_UI_STYLE_TOKENS


@dataclass(frozen=True, slots=True)
class _ResolvedButtonStyle:
    bg_color: str
    border_color: str
    highlight_color: str
    text_color: str
    radius: float
    border_thickness: float
    glossy: bool
    shadow_enabled: bool
    shadow_color: str
    shadow_layers: int
    shadow_spread: float
    shadow_offset_x: float
    shadow_offset_y: float
    highlight_height_ratio: float


class GameView:
    """Draws game state using retained keyed scene nodes."""

    def __init__(self, renderer: Render2D, layout: GridLayout) -> None:
        self._renderer = renderer
        self._layout = layout
        self._theme: SceneTheme = theme_for_state(AppState.MAIN_MENU)

    def render(
        self,
        ui: AppUIState,
        debug_ui: bool,
        debug_labels_state: list[str],
    ) -> list[str]:
        """Draw current app state and return latest button labels for debug."""
        self._theme = theme_for_state(ui.state)
        self._renderer.begin_frame()
        self._renderer.fill_window("bg:window", self._theme.window_bg, z=-100.0)

        labels = self._draw_buttons(ui.buttons)
        if ui.state in (AppState.PLACEMENT_EDIT, AppState.BATTLE, AppState.RESULT):
            draw_player_board(
                renderer=self._renderer,
                layout=self._layout,
                placements=ui.placements,
                session=ui.session,
                held_ship_type=ui.held_ship_type,
                held_orientation=ui.held_ship_orientation,
                held_grab_index=ui.held_grab_index,
                hover_cell=ui.hover_cell,
                hover_x=ui.hover_x,
                hover_y=ui.hover_y,
                theme=self._theme,
            )
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            draw_ai_board(
                renderer=self._renderer,
                layout=self._layout,
                session=ui.session,
                theme=self._theme,
            )
        if ui.state is AppState.PLACEMENT_EDIT:
            draw_placement_panel(self._renderer, ui.placements, ui.ship_order, theme=self._theme)
        if ui.state is AppState.PRESET_MANAGE:
            draw_preset_manage(self._renderer, ui, theme=self._theme)
        if ui.state is AppState.NEW_GAME_SETUP:
            draw_new_game_setup(self._renderer, ui, theme=self._theme)

        prompt_widget = build_modal_text_input_widget(ui)
        if prompt_widget is not None:
            render_modal_text_input_widget(self._renderer, prompt_widget)

        draw_status_bar(
            renderer=self._renderer,
            state=ui.state,
            status=ui.status,
            placement_orientation=ui.placement_orientation,
            placements=ui.placements,
            ship_order=ui.ship_order,
            theme=self._theme,
        )
        self._renderer.set_title(f"Warships V1 | {ui.status}")

        if debug_ui and labels != debug_labels_state:
            logger.debug("ui_button_labels labels=%s", labels)
        self._renderer.end_frame()
        return labels

    def _draw_buttons(self, buttons: list[Button]) -> list[str]:
        labels: list[str] = []
        for button in buttons:
            if (
                is_new_game_custom_button(button.id)
                or button.id.startswith("preset_edit:")
                or button.id.startswith("preset_rename:")
                or button.id.startswith("preset_delete:")
            ):
                continue
            style = self._resolve_button_chrome(button)
            z = 10.4 if button.id.startswith("prompt_") else 1.0
            if style.shadow_enabled:
                draw_shadow_rect(
                    self._renderer,
                    key=f"button:shadow:{button.id}",
                    x=button.x + style.shadow_offset_x,
                    y=button.y + style.shadow_offset_y,
                    w=button.w,
                    h=button.h,
                    color=style.shadow_color,
                    layers=style.shadow_layers,
                    spread=style.shadow_spread,
                    corner_radius=style.radius,
                    z=z - 0.02,
                )
            draw_rounded_rect(
                self._renderer,
                key=f"button:bg:{button.id}",
                x=button.x,
                y=button.y,
                w=button.w,
                h=button.h,
                radius=style.radius,
                color=style.bg_color,
                z=z,
            )
            draw_rounded_rect(
                self._renderer,
                key=f"button:border:{button.id}",
                x=button.x,
                y=button.y,
                w=button.w,
                h=button.h,
                radius=style.radius,
                color=style.border_color,
                z=z + 0.02,
            )
            draw_rounded_rect(
                self._renderer,
                key=f"button:border:inner:{button.id}",
                x=button.x + style.border_thickness,
                y=button.y + style.border_thickness,
                w=max(1.0, button.w - (2.0 * style.border_thickness)),
                h=max(1.0, button.h - (2.0 * style.border_thickness)),
                radius=max(0.0, style.radius - style.border_thickness),
                color=style.bg_color,
                z=z + 0.021,
            )
            if style.glossy:
                draw_rounded_rect(
                    self._renderer,
                    key=f"button:highlight:{button.id}",
                    x=button.x + style.border_thickness,
                    y=button.y + style.border_thickness,
                    w=max(1.0, button.w - (2.0 * style.border_thickness)),
                    h=max(1.0, (button.h * style.highlight_height_ratio) - style.border_thickness),
                    radius=max(0.0, style.radius - style.border_thickness),
                    color=style.highlight_color,
                    z=z + 0.03,
                )
            label = button_label(button.id)
            fitted_label, fitted_font_size = fit_text_to_rect(
                label,
                rect_w=button.w,
                rect_h=button.h,
                base_font_size=17.0,
                overflow_policy="ellipsis",
            )
            labels.append(fitted_label)
            self._renderer.add_text(
                key=f"button:text:{button.id}",
                text=fitted_label,
                x=button.x + button.w / 2.0,
                y=button.y + button.h / 2.0,
                font_size=fitted_font_size,
                color=style.text_color,
                anchor="middle-center",
                z=10.5 if button.id.startswith("prompt_") else 3.0,
            )
        return labels

    @staticmethod
    def _button_semantic(button_id: str) -> str:
        normalized = str(button_id).strip().lower()
        if normalized.startswith("preset_delete:"):
            return "danger"
        if normalized.startswith("prompt_cancel"):
            return "secondary"
        return "primary"

    def _resolve_button_chrome(self, button: Button) -> _ResolvedButtonStyle:
        from engine.api.ui_primitives import ButtonStyle

        style_obj = button.style if isinstance(button.style, ButtonStyle) else None
        style = button.style if isinstance(button.style, dict) else {}
        enabled = bool(button.enabled)

        def _pick(name: str) -> object | None:
            if style_obj is not None and hasattr(style_obj, name):
                return cast(object, getattr(style_obj, name))
            return style.get(name)

        bg_override = _pick("bg_color")
        border_override = _pick("border_color")
        highlight_override = _pick("highlight_color")
        text_override = _pick("text_color")
        radius_override = _pick("radius")
        border_thickness_override = _pick("border_thickness")
        glossy_override = _pick("glossy")
        shadow_enabled_override = _pick("shadow_enabled")
        shadow_color_override = _pick("shadow_color")
        shadow_layers_override = _pick("shadow_layers")
        shadow_spread_override = _pick("shadow_spread")
        shadow_offset_x_override = _pick("shadow_offset_x")
        shadow_offset_y_override = _pick("shadow_offset_y")
        highlight_ratio_override = _pick("highlight_height_ratio")

        semantic = self._button_semantic(button.id)
        base_bg = self._theme.primary_button_bg if enabled else TOKENS.accent_muted
        base_border = self._theme.primary_button_border if enabled else TOKENS.border_subtle
        base_highlight = (
            self._theme.primary_button_highlight if enabled else TOKENS.highlight_top_subtle
        )
        base_text = TOKENS.text_on_accent
        base_glossy = True
        if semantic == "danger" and enabled:
            base_bg = self._theme.danger_button_bg
            base_border = self._theme.danger_button_border
            base_highlight = TOKENS.highlight_top_subtle
        elif semantic == "secondary":
            if enabled:
                base_bg = self._theme.secondary_button_bg
                base_border = self._theme.secondary_button_border
                base_highlight = TOKENS.highlight_top_subtle
            else:
                base_bg = TOKENS.surface_overlay
                base_border = TOKENS.border_subtle
                base_highlight = TOKENS.highlight_bottom_clear
                base_glossy = False
            base_text = TOKENS.text_primary

        bg = str(bg_override) if isinstance(bg_override, str) else base_bg
        border = str(border_override) if isinstance(border_override, str) else base_border
        highlight = (
            str(highlight_override)
            if isinstance(highlight_override, str)
            else base_highlight
        )
        text = str(text_override) if isinstance(text_override, str) else base_text
        radius = max(0.0, float(radius_override)) if isinstance(radius_override, (int, float)) else 8.0
        border_thickness = (
            max(1.0, float(border_thickness_override))
            if isinstance(border_thickness_override, (int, float))
            else 1.0
        )
        glossy = bool(glossy_override) if isinstance(glossy_override, bool) else base_glossy
        shadow_enabled = bool(shadow_enabled_override) if isinstance(shadow_enabled_override, bool) else False
        shadow_color = (
            str(shadow_color_override)
            if isinstance(shadow_color_override, str)
            else (TOKENS.shadow_strong if shadow_enabled else TOKENS.shadow_soft)
        )
        shadow_layers = max(1, int(shadow_layers_override)) if isinstance(shadow_layers_override, int) else 1
        shadow_spread = (
            max(1.0, float(shadow_spread_override))
            if isinstance(shadow_spread_override, (int, float))
            else 2.25
        )
        shadow_offset_x = (
            float(shadow_offset_x_override)
            if isinstance(shadow_offset_x_override, (int, float))
            else 0.0
        )
        shadow_offset_y = (
            float(shadow_offset_y_override)
            if isinstance(shadow_offset_y_override, (int, float))
            else 2.0
        )
        highlight_height_ratio = (
            min(1.0, max(0.1, float(highlight_ratio_override)))
            if isinstance(highlight_ratio_override, (int, float))
            else 0.45
        )
        return _ResolvedButtonStyle(
            bg_color=bg,
            border_color=border,
            highlight_color=highlight,
            text_color=text,
            radius=radius,
            border_thickness=border_thickness,
            glossy=glossy,
            shadow_enabled=shadow_enabled,
            shadow_color=shadow_color,
            shadow_layers=shadow_layers,
            shadow_spread=shadow_spread,
            shadow_offset_x=shadow_offset_x,
            shadow_offset_y=shadow_offset_y,
            highlight_height_ratio=highlight_height_ratio,
        )

    def build_snapshot(
        self,
        *,
        frame_index: int,
        ui: AppUIState,
        debug_ui: bool,
        debug_labels_state: list[str],
    ) -> tuple[RenderSnapshot, list[str]]:
        """Build immutable render snapshot for current UI state."""
        recorder = _SnapshotRecorder()
        snapshot_view = GameView(recorder, self._layout)
        labels = snapshot_view.render(
            ui=ui,
            debug_ui=debug_ui,
            debug_labels_state=debug_labels_state,
        )
        return recorder.finish(frame_index=frame_index), labels


class _SnapshotRecorder:
    """RenderAPI-compatible recorder that captures immutable snapshot commands."""

    def __init__(self) -> None:
        self._commands: list[RenderCommand] = []

    def begin_frame(self) -> None:
        return

    def end_frame(self) -> None:
        return

    def add_rect(
        self,
        key: str | None,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
    ) -> None:
        self._commands.append(
            RenderCommand(
                kind="rect",
                layer=int(round(z * 100.0)),
                transform=mat4_translation(Vec3(x=float(x), y=float(y), z=float(z))),
                data=(
                    ("key", key),
                    ("x", float(x)),
                    ("y", float(y)),
                    ("w", float(w)),
                    ("h", float(h)),
                    ("color", str(color)),
                    ("z", float(z)),
                    ("static", bool(static)),
                ),
            )
        )

    def add_style_rect(
        self,
        *,
        style_kind: str,
        key: str,
        x: float,
        y: float,
        w: float,
        h: float,
        color: str,
        z: float = 0.0,
        static: bool = False,
        radius: float = 0.0,
        thickness: float = 1.0,
        color_secondary: str = "",
        shadow_layers: float = 0.0,
        **extra: object,
    ) -> None:
        # Snapshot recorder is intentionally forward-compatible with new style
        # rectangle fields to avoid runtime crashes when API evolves.
        extra_pairs = tuple(
            (str(name), value)
            for name, value in sorted(extra.items())
            if isinstance(value, (str, int, float, bool))
        )
        self._commands.append(
            RenderCommand(
                kind=str(style_kind),
                layer=int(round(float(z) * 100.0)),
                transform=mat4_translation(Vec3(x=float(x), y=float(y), z=float(z))),
                data=(
                    ("key", str(key)),
                    ("x", float(x)),
                    ("y", float(y)),
                    ("w", float(w)),
                    ("h", float(h)),
                    ("color", str(color)),
                    ("z", float(z)),
                    ("static", bool(static)),
                    ("radius", float(radius)),
                    ("thickness", float(thickness)),
                    ("color_secondary", str(color_secondary)),
                    ("shadow_layers", float(shadow_layers)),
                    *extra_pairs,
                ),
            )
        )

    def add_grid(
        self,
        key: str,
        x: float,
        y: float,
        width: float,
        height: float,
        lines: int,
        color: str,
        z: float = 0.5,
        static: bool = False,
    ) -> None:
        self._commands.append(
            RenderCommand(
                kind="grid",
                layer=int(round(z * 100.0)),
                transform=mat4_translation(Vec3(x=float(x), y=float(y), z=float(z))),
                data=(
                    ("key", key),
                    ("x", float(x)),
                    ("y", float(y)),
                    ("width", float(width)),
                    ("height", float(height)),
                    ("lines", int(lines)),
                    ("color", str(color)),
                    ("z", float(z)),
                    ("static", bool(static)),
                ),
            )
        )

    def add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = DEFAULT_UI_STYLE_TOKENS.text_primary,
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        self._commands.append(
            RenderCommand(
                kind="text",
                layer=int(round(z * 100.0)),
                transform=mat4_translation(Vec3(x=float(x), y=float(y), z=float(z))),
                data=(
                    ("key", key),
                    ("text", str(text)),
                    ("x", float(x)),
                    ("y", float(y)),
                    ("font_size", float(font_size)),
                    ("color", str(color)),
                    ("anchor", str(anchor)),
                    ("z", float(z)),
                    ("static", bool(static)),
                ),
            )
        )

    def set_title(self, title: str) -> None:
        self._commands.append(
            RenderCommand(
                kind="title",
                layer=0,
                transform=mat4_translation(Vec3(0.0, 0.0, 0.0)),
                data=(("title", str(title)),),
            )
        )

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        self._commands.append(
            RenderCommand(
                kind="fill_window",
                layer=int(round(z * 100.0)),
                transform=mat4_translation(Vec3(0.0, 0.0, float(z))),
                data=(
                    ("key", str(key)),
                    ("color", str(color)),
                    ("z", float(z)),
                ),
            )
        )

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (x, y)

    def invalidate(self) -> None:
        return

    def run(self, draw_callback: Callable[[], None]) -> None:
        _ = draw_callback
        return

    def close(self) -> None:
        return

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        _ = snapshot
        return

    def finish(self, *, frame_index: int) -> RenderSnapshot:
        commands = tuple(
            sorted(
                self._commands,
                key=lambda command: (
                    int(getattr(command, "layer", 0)),
                    str(getattr(command, "kind", "")),
                    str(getattr(command, "sort_key", "")),
                ),
            )
        )
        return RenderSnapshot(
            frame_index=int(frame_index),
            passes=(RenderPassSnapshot(name="ui", commands=commands),),
        )

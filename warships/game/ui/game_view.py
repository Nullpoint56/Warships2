"""Retained-mode game rendering for Warships."""

from __future__ import annotations

import logging
from collections.abc import Callable

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
    draw_stroke_rect,
)
from warships.game.app.state_machine import AppState
from warships.game.app.ui_state import AppUIState
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


class GameView:
    """Draws game state using retained keyed scene nodes."""

    def __init__(self, renderer: Render2D, layout: GridLayout) -> None:
        self._renderer = renderer
        self._layout = layout

    def render(
        self,
        ui: AppUIState,
        debug_ui: bool,
        debug_labels_state: list[str],
    ) -> list[str]:
        """Draw current app state and return latest button labels for debug."""
        self._renderer.begin_frame()
        self._renderer.fill_window("bg:window", TOKENS.window_bg, z=-100.0)

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
            )
        if ui.state in (AppState.BATTLE, AppState.RESULT):
            draw_ai_board(renderer=self._renderer, layout=self._layout, session=ui.session)
        if ui.state is AppState.PLACEMENT_EDIT:
            draw_placement_panel(self._renderer, ui.placements, ui.ship_order)
        if ui.state is AppState.PRESET_MANAGE:
            draw_preset_manage(self._renderer, ui)
        if ui.state is AppState.NEW_GAME_SETUP:
            draw_new_game_setup(self._renderer, ui)

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
        )
        self._renderer.set_title(f"Warships V1 | {ui.status}")

        if debug_ui and labels != debug_labels_state:
            logger.debug("ui_button_labels labels=%s", labels)
        self._renderer.end_frame()
        return labels

    def _draw_buttons(self, buttons: list[Button]) -> list[str]:
        labels: list[str] = []
        for button in buttons:
            if is_new_game_custom_button(button.id):
                continue
            color = TOKENS.accent if button.enabled else TOKENS.accent_muted
            z = 10.4 if button.id.startswith("prompt_") else 1.0
            draw_rounded_rect(
                self._renderer,
                key=f"button:bg:{button.id}",
                x=button.x,
                y=button.y,
                w=button.w,
                h=button.h,
                radius=8.0,
                color=color,
                z=z,
            )
            draw_stroke_rect(
                self._renderer,
                key=f"button:border:{button.id}",
                x=button.x,
                y=button.y,
                w=button.w,
                h=button.h,
                color=TOKENS.border_accent if button.enabled else TOKENS.border_subtle,
                thickness=1.0,
                z=z + 0.02,
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
                color=TOKENS.text_on_accent,
                anchor="middle-center",
                z=10.5 if button.id.startswith("prompt_") else 3.0,
            )
        return labels

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
        labels = snapshot_view.render(ui=ui, debug_ui=debug_ui, debug_labels_state=debug_labels_state)
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
    ) -> None:
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

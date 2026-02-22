"""Debug overlay snapshot capture helpers for EngineHost."""

from __future__ import annotations

from collections.abc import Callable

from engine.api.render import RenderAPI
from engine.api.render_snapshot import IDENTITY_MAT4, RenderCommand, RenderPassSnapshot, RenderSnapshot
from engine.api.window import WindowResizeEvent
from engine.runtime.metrics import MetricsSnapshot
from engine.ui_runtime.debug_overlay import DebugOverlay


class OverlaySnapshotRecorder(RenderAPI):
    """Capture debug overlay primitives into immutable render commands."""

    def __init__(self, *, frame_index: int) -> None:
        self._frame_index = int(frame_index)
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
                layer=int(round(float(z) * 100.0)),
                transform=IDENTITY_MAT4,
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
                layer=int(round(float(z) * 100.0)),
                transform=IDENTITY_MAT4,
                data=(
                    ("key", str(key)),
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
    ) -> None:
        _ = (style_kind, radius, thickness, color_secondary, shadow_layers)
        self.add_rect(key, x, y, w, h, color, z=z, static=static)

    def add_text(
        self,
        key: str | None,
        text: str,
        x: float,
        y: float,
        font_size: float = 18.0,
        color: str = "#ffffff",
        anchor: str = "top-left",
        z: float = 2.0,
        static: bool = False,
    ) -> None:
        self._commands.append(
            RenderCommand(
                kind="text",
                layer=int(round(float(z) * 100.0)),
                transform=IDENTITY_MAT4,
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
                transform=IDENTITY_MAT4,
                data=(("title", str(title)),),
            )
        )

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        self._commands.append(
            RenderCommand(
                kind="fill_window",
                layer=int(round(float(z) * 100.0)),
                transform=IDENTITY_MAT4,
                data=(("key", str(key)), ("color", str(color)), ("z", float(z))),
            )
        )

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return (float(x), float(y))

    def design_space_size(self) -> tuple[float, float]:
        return (1200.0, 720.0)

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

    def apply_window_resize(self, event: WindowResizeEvent) -> None:
        _ = event
        return

    def snapshot(self) -> RenderSnapshot | None:
        if not self._commands:
            return None
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
            frame_index=self._frame_index,
            passes=(RenderPassSnapshot(name="debug_overlay", commands=commands),),
        )


def build_overlay_snapshot(
    *,
    frame_index: int,
    overlay: DebugOverlay,
    snapshot: MetricsSnapshot,
    ui_diagnostics: dict[str, int] | None,
) -> RenderSnapshot | None:
    recorder = OverlaySnapshotRecorder(frame_index=frame_index)
    overlay.draw(recorder, snapshot, ui_diagnostics=ui_diagnostics)
    return recorder.snapshot()


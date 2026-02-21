"""Engine-neutral UI coordinate-space transform helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from engine.api.render import RenderAPI
from engine.api.render_snapshot import RenderCommand, RenderPassSnapshot, RenderSnapshot


@dataclass(frozen=True, slots=True)
class UISpaceTransform:
    """Bidirectional mapping between engine design-space and app authored-space."""

    engine_width: float
    engine_height: float
    app_width: float
    app_height: float

    @property
    def scale_x(self) -> float:
        return self.engine_width / self.app_width

    @property
    def scale_y(self) -> float:
        return self.engine_height / self.app_height

    @property
    def font_scale(self) -> float:
        return min(self.scale_x, self.scale_y)

    @property
    def is_identity(self) -> bool:
        return abs(self.scale_x - 1.0) <= 1e-6 and abs(self.scale_y - 1.0) <= 1e-6

    def engine_to_app(self, x: float, y: float) -> tuple[float, float]:
        return (float(x) / self.scale_x, float(y) / self.scale_y)

    def app_to_engine(self, x: float, y: float) -> tuple[float, float]:
        return (float(x) * self.scale_x, float(y) * self.scale_y)


def resolve_ui_space_transform(*, app: object, renderer: RenderAPI) -> UISpaceTransform:
    """Resolve app<->engine UI transform using app authored resolution when provided."""
    engine_w, engine_h = _resolve_engine_design_resolution(renderer)
    app_design = _resolve_app_design_resolution(app)
    if app_design is None:
        return UISpaceTransform(
            engine_width=engine_w,
            engine_height=engine_h,
            app_width=engine_w,
            app_height=engine_h,
        )
    app_w, app_h = app_design
    return UISpaceTransform(
        engine_width=engine_w,
        engine_height=engine_h,
        app_width=app_w,
        app_height=app_h,
    )


def create_app_render_api(*, app: object, renderer: RenderAPI) -> RenderAPI:
    """Return app-facing renderer that scales authored coordinates into engine design-space."""
    transform = resolve_ui_space_transform(app=app, renderer=renderer)
    if transform.is_identity:
        return renderer
    return _ScaledRenderAPI(inner=renderer, transform=transform)


def _resolve_app_design_resolution(app: object) -> tuple[float, float] | None:
    provider = getattr(app, "ui_design_resolution", None)
    if not callable(provider):
        return None
    try:
        raw = provider()
    except Exception:
        return None
    if not isinstance(raw, tuple) or len(raw) != 2:
        return None
    try:
        width = float(raw[0])
        height = float(raw[1])
    except (TypeError, ValueError):
        return None
    if width <= 0.0 or height <= 0.0:
        return None
    return (width, height)


def _resolve_engine_design_resolution(renderer: RenderAPI) -> tuple[float, float]:
    provider = getattr(renderer, "design_space_size", None)
    if callable(provider):
        try:
            raw = provider()
        except Exception:
            raw = None
        if isinstance(raw, tuple) and len(raw) == 2:
            try:
                width = float(raw[0])
                height = float(raw[1])
            except (TypeError, ValueError):
                width = 0.0
                height = 0.0
            if width > 0.0 and height > 0.0:
                return (width, height)
    return _resolve_design_resolution_from_env()


def _resolve_design_resolution_from_env() -> tuple[float, float]:
    raw = os.getenv("ENGINE_UI_RESOLUTION", "").strip().lower()
    if raw:
        normalized = raw.replace(" ", "")
        for sep in ("x", ",", ":"):
            if sep in normalized:
                left, right = normalized.split(sep, 1)
                try:
                    width = float(max(1, int(left)))
                    height = float(max(1, int(right)))
                except ValueError:
                    break
                return (width, height)
    return (1200.0, 720.0)


class _ScaledRenderAPI:
    """RenderAPI proxy that maps app-authored coordinates to engine design-space."""

    def __init__(self, *, inner: RenderAPI, transform: UISpaceTransform) -> None:
        self._inner = inner
        self._transform = transform

    def begin_frame(self) -> None:
        self._inner.begin_frame()

    def end_frame(self) -> None:
        self._inner.end_frame()

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
        ex, ey = self._transform.app_to_engine(x, y)
        self._inner.add_rect(
            key,
            ex,
            ey,
            float(w) * self._transform.scale_x,
            float(h) * self._transform.scale_y,
            color,
            z=z,
            static=static,
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
        add_style_rect = getattr(self._inner, "add_style_rect", None)
        if not callable(add_style_rect):
            self.add_rect(key, x, y, w, h, color, z=z, static=static)
            return
        ex, ey = self._transform.app_to_engine(x, y)
        add_style_rect(
            style_kind=str(style_kind),
            key=str(key),
            x=ex,
            y=ey,
            w=float(w) * self._transform.scale_x,
            h=float(h) * self._transform.scale_y,
            color=str(color),
            z=float(z),
            static=bool(static),
            radius=float(radius) * min(self._transform.scale_x, self._transform.scale_y),
            thickness=float(thickness) * min(self._transform.scale_x, self._transform.scale_y),
            color_secondary=str(color_secondary),
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
        ex, ey = self._transform.app_to_engine(x, y)
        self._inner.add_grid(
            key=key,
            x=ex,
            y=ey,
            width=float(width) * self._transform.scale_x,
            height=float(height) * self._transform.scale_y,
            lines=lines,
            color=color,
            z=z,
            static=static,
        )

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
        ex, ey = self._transform.app_to_engine(x, y)
        self._inner.add_text(
            key=key,
            text=text,
            x=ex,
            y=ey,
            font_size=float(font_size) * self._transform.font_scale,
            color=color,
            anchor=anchor,
            z=z,
            static=static,
        )

    def set_title(self, title: str) -> None:
        self._inner.set_title(title)

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        self._inner.fill_window(key=key, color=color, z=z)

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        ex, ey = self._inner.to_design_space(x, y)
        return self._transform.engine_to_app(ex, ey)

    def invalidate(self) -> None:
        self._inner.invalidate()

    def run(self, draw_callback: Any) -> None:
        self._inner.run(draw_callback)

    def close(self) -> None:
        self._inner.close()

    def render_snapshot(self, snapshot: RenderSnapshot) -> None:
        self._inner.render_snapshot(scale_render_snapshot(snapshot, self._transform))

    def design_space_size(self) -> tuple[float, float]:
        return (self._transform.app_width, self._transform.app_height)


def _scale_render_snapshot(snapshot: RenderSnapshot, transform: UISpaceTransform) -> RenderSnapshot:
    scaled_passes = tuple(
        RenderPassSnapshot(
            name=str(render_pass.name),
            commands=tuple(
                _scale_render_command(command, transform) for command in render_pass.commands
            ),
        )
        for render_pass in snapshot.passes
    )
    return RenderSnapshot(frame_index=int(snapshot.frame_index), passes=scaled_passes)


def scale_render_snapshot(snapshot: RenderSnapshot, transform: UISpaceTransform) -> RenderSnapshot:
    """Scale immutable snapshot command payload from app-space into engine-space."""
    if transform.is_identity:
        return snapshot
    return _scale_render_snapshot(snapshot, transform)


def _scale_render_command(command: RenderCommand, transform: UISpaceTransform) -> RenderCommand:
    sx = float(transform.scale_x)
    sy = float(transform.scale_y)
    font_scale = float(transform.font_scale)
    scaled_data: list[tuple[str, object]] = []
    for key, value in command.data:
        name = str(key)
        if isinstance(value, (int, float)):
            number = float(value)
            if name in {"x", "width", "w"}:
                scaled_data.append((name, number * sx))
                continue
            if name in {"y", "height", "h"}:
                scaled_data.append((name, number * sy))
                continue
            if name in {"radius", "thickness"}:
                scaled_data.append((name, number * font_scale))
                continue
            if name == "font_size":
                scaled_data.append((name, number * font_scale))
                continue
        scaled_data.append((name, value))
    return RenderCommand(
        kind=str(command.kind),
        layer=int(command.layer),
        sort_key=str(command.sort_key),
        transform=command.transform,
        data=tuple(scaled_data),
    )

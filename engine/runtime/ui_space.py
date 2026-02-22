"""Engine-neutral UI coordinate-space transform helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.api.app_port import EngineAppPort, UIDesignResolutionProvider
from engine.api.render import RenderAPI
from engine.api.render_snapshot import (
    RenderCommand,
    RenderDataValue,
    RenderPassSnapshot,
    RenderSnapshot,
)
from engine.api.window import WindowResizeEvent
from engine.runtime.config import get_runtime_config

_SCALE_CACHE_MAX = 20_000
_SCALED_COMMAND_CACHE: dict[
    tuple[int, tuple[float, float, float]],
    tuple[RenderCommand, RenderCommand],
] = {}
_SCALED_PASS_CACHE: dict[
    tuple[int, tuple[float, float, float]],
    tuple[tuple[RenderCommand, ...], tuple[RenderCommand, ...]],
] = {}


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


def resolve_ui_space_transform(
    *,
    design_resolution_provider: UIDesignResolutionProvider | None,
    renderer: RenderAPI,
) -> UISpaceTransform:
    """Resolve app<->engine UI transform using app authored resolution when provided."""
    engine_w, engine_h = _resolve_engine_design_resolution(renderer)
    app_design = _resolve_app_design_resolution(design_resolution_provider)
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


def create_app_render_api(*, app: EngineAppPort, renderer: RenderAPI) -> RenderAPI:
    """Return app-facing renderer that scales authored coordinates into engine design-space."""
    provider = app if isinstance(app, UIDesignResolutionProvider) else None
    transform = resolve_ui_space_transform(design_resolution_provider=provider, renderer=renderer)
    if transform.is_identity:
        return renderer
    return _ScaledRenderAPI(inner=renderer, transform=transform)


def _resolve_app_design_resolution(
    provider: UIDesignResolutionProvider | None,
) -> tuple[float, float] | None:
    if provider is None:
        return None
    try:
        raw = provider.ui_design_resolution()
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
    try:
        raw = renderer.design_space_size()
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
    return _resolve_design_resolution_from_config()


def _resolve_design_resolution_from_config() -> tuple[float, float]:
    runtime_config = get_runtime_config()
    resolution = runtime_config.render.ui_resolution
    if resolution is not None:
        return (float(resolution[0]), float(resolution[1]))
    return (
        float(runtime_config.render.ui_design_width),
        float(runtime_config.render.ui_design_height),
    )


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
        shadow_layers: float = 0.0,
    ) -> None:
        ex, ey = self._transform.app_to_engine(x, y)
        self._inner.add_style_rect(
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
            shadow_layers=float(shadow_layers),
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

    def apply_window_resize(self, event: WindowResizeEvent) -> None:
        self._inner.apply_window_resize(event)


def _scale_render_snapshot(snapshot: RenderSnapshot, transform: UISpaceTransform) -> RenderSnapshot:
    scale_key = (
        round(float(transform.scale_x), 6),
        round(float(transform.scale_y), 6),
        round(float(transform.font_scale), 6),
    )
    scaled_passes = tuple(
        RenderPassSnapshot(
            name=str(render_pass.name),
            commands=_scale_render_commands(
                render_pass.commands,
                transform,
                scale_key=scale_key,
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
    scaled_data: list[tuple[str, RenderDataValue]] = []
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


def _scale_render_commands(
    commands: tuple[RenderCommand, ...],
    transform: UISpaceTransform,
    *,
    scale_key: tuple[float, float, float],
) -> tuple[RenderCommand, ...]:
    pass_cache_key = (int(id(commands)), scale_key)
    cached_pass = _SCALED_PASS_CACHE.get(pass_cache_key)
    if cached_pass is not None and cached_pass[0] is commands:
        return cached_pass[1]
    scaled = tuple(
        _scale_render_command_cached(command, transform, scale_key=scale_key)
        for command in commands
    )
    _SCALED_PASS_CACHE[pass_cache_key] = (commands, scaled)
    if len(_SCALED_PASS_CACHE) > _SCALE_CACHE_MAX:
        _SCALED_PASS_CACHE.clear()
        _SCALED_PASS_CACHE[pass_cache_key] = (commands, scaled)
    return scaled


def _scale_render_command_cached(
    command: RenderCommand,
    transform: UISpaceTransform,
    *,
    scale_key: tuple[float, float, float],
) -> RenderCommand:
    cache_key = (int(id(command)), scale_key)
    cached = _SCALED_COMMAND_CACHE.get(cache_key)
    if cached is not None and cached[0] is command:
        return cached[1]
    scaled = _scale_render_command(command, transform)
    _SCALED_COMMAND_CACHE[cache_key] = (command, scaled)
    if len(_SCALED_COMMAND_CACHE) > _SCALE_CACHE_MAX:
        _SCALED_COMMAND_CACHE.clear()
        _SCALED_COMMAND_CACHE[cache_key] = (command, scaled)
    return scaled

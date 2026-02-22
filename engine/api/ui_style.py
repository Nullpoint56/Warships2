"""Engine-owned UI style tokens and renderer-agnostic shape primitives."""

from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass

from engine.api.render import RenderAPI


@dataclass(frozen=True, slots=True)
class UIStyleTokens:
    """Deterministic default style tokens for 2D UI scenes."""

    window_bg: str = "#0a1220"
    surface_base: str = "#111a2b"
    surface_elevated: str = "#18243a"
    surface_overlay: str = "#0d1626"
    border_subtle: str = "#2e3e57"
    border_accent: str = "#4f8cff"
    accent: str = "#0e66f2"
    accent_hover: str = "#2a7bff"
    accent_muted: str = "#2b3f66"
    danger: str = "#d14343"
    success: str = "#14b86a"
    success_muted: str = "#0f8c53"
    warning: str = "#f59e0b"
    board_bg: str = "#163e8a"
    board_grid: str = "#73a7ff"
    text_primary: str = "#f7faff"
    text_secondary: str = "#c7d5ec"
    text_muted: str = "#92a8c8"
    text_on_accent: str = "#ffffff"
    shadow_soft: str = "#00000055"
    shadow_strong: str = "#00000088"
    highlight_top_soft: str = "#ffffff1f"
    highlight_top_medium: str = "#ffffff22"
    highlight_top_subtle: str = "#ffffff14"
    highlight_bottom_clear: str = "#ffffff00"


DEFAULT_UI_STYLE_TOKENS = UIStyleTokens()
_STYLE_EFFECTS_ENABLED: ContextVar[bool] = ContextVar("engine_ui_style_effects_enabled", default=True)


def configure_style_effects(*, enabled: bool) -> None:
    """Set global style-effects switch resolved by runtime configuration."""
    _STYLE_EFFECTS_ENABLED.set(bool(enabled))


def _style_effects_enabled() -> bool:
    return bool(_STYLE_EFFECTS_ENABLED.get())


def draw_stroke_rect(
    renderer: RenderAPI,
    *,
    key: str,
    x: float,
    y: float,
    w: float,
    h: float,
    color: str,
    thickness: float = 1.0,
    z: float = 0.0,
    static: bool = False,
) -> None:
    """Draw rectangle stroke."""
    if not _style_effects_enabled():
        return
    if _add_style_rect(
        renderer,
        style_kind="stroke_rect",
        key=key,
        x=x,
        y=y,
        w=w,
        h=h,
        color=color,
        z=z,
        static=static,
        thickness=thickness,
    ):
        return
    t = max(1.0, float(thickness))
    if w <= 0.0 or h <= 0.0:
        return
    renderer.add_rect(f"{key}:top", x, y, w, t, color, z=z, static=static)
    renderer.add_rect(f"{key}:bottom", x, y + h - t, w, t, color, z=z, static=static)
    renderer.add_rect(f"{key}:left", x, y, t, h, color, z=z, static=static)
    renderer.add_rect(f"{key}:right", x + w - t, y, t, h, color, z=z, static=static)


def draw_gradient_rect(
    renderer: RenderAPI,
    *,
    key: str,
    x: float,
    y: float,
    w: float,
    h: float,
    top_color: str,
    bottom_color: str,
    z: float = 0.0,
    steps: int = 8,
    static: bool = False,
) -> None:
    """Draw vertical gradient."""
    if not _style_effects_enabled():
        return
    if _add_style_rect(
        renderer,
        style_kind="gradient_rect",
        key=key,
        x=x,
        y=y,
        w=w,
        h=h,
        color=top_color,
        z=z,
        static=static,
        color_secondary=bottom_color,
    ):
        return
    if w <= 0.0 or h <= 0.0:
        return
    n = max(1, int(steps))
    top = _parse_hex_rgba(top_color)
    bottom = _parse_hex_rgba(bottom_color)
    strip_h = h / float(n)
    for i in range(n):
        mix = float(i) / float(max(1, n - 1))
        color = _format_rgba(
            (
                _lerp(top[0], bottom[0], mix),
                _lerp(top[1], bottom[1], mix),
                _lerp(top[2], bottom[2], mix),
                _lerp(top[3], bottom[3], mix),
            )
        )
        renderer.add_rect(
            f"{key}:step:{i}",
            x,
            y + (float(i) * strip_h),
            w,
            max(1.0, strip_h + 0.5),
            color,
            z=z,
            static=static,
        )


def draw_shadow_rect(
    renderer: RenderAPI,
    *,
    key: str,
    x: float,
    y: float,
    w: float,
    h: float,
    color: str = "#00000055",
    layers: int = 2,
    spread: float = 2.0,
    corner_radius: float = 0.0,
    z: float = 0.0,
    static: bool = False,
) -> None:
    """Draw soft shadow."""
    if not _style_effects_enabled():
        return
    if _add_style_rect(
        renderer,
        style_kind="shadow_rect",
        key=key,
        x=x,
        y=y,
        w=w,
        h=h,
        color=color,
        z=z,
        static=static,
        thickness=spread,
        radius=corner_radius,
        shadow_layers=float(layers),
    ):
        return
    if w <= 0.0 or h <= 0.0:
        return
    rgba = _parse_hex_rgba(color)
    count = max(1, int(layers))
    for i in range(count, 0, -1):
        k = float(i) / float(count)
        alpha = rgba[3] * (k * 0.6)
        pad = float(i) * float(spread)
        renderer.add_rect(
            f"{key}:layer:{i}",
            x - pad,
            y - pad,
            w + 2.0 * pad,
            h + 2.0 * pad,
            _format_rgba((rgba[0], rgba[1], rgba[2], alpha)),
            z=z - (0.001 * float(i)),
            static=static,
        )


def draw_rounded_rect(
    renderer: RenderAPI,
    *,
    key: str,
    x: float,
    y: float,
    w: float,
    h: float,
    radius: float,
    color: str,
    z: float = 0.0,
    static: bool = False,
) -> None:
    """Draw rounded rect; defaults to fast rectangular fallback unless effects enabled."""
    if w <= 0.0 or h <= 0.0:
        return
    if not _style_effects_enabled():
        renderer.add_rect(key, x, y, w, h, color, z=z, static=static)
        return
    if _add_style_rect(
        renderer,
        style_kind="rounded_rect",
        key=key,
        x=x,
        y=y,
        w=w,
        h=h,
        color=color,
        z=z,
        static=static,
        radius=radius,
    ):
        return
    r = min(float(radius), w * 0.5, h * 0.5)
    if r < 1.0:
        renderer.add_rect(key, x, y, w, h, color, z=z, static=static)
        return
    rows = int(max(1, round(r)))
    body_y = y + r
    body_h = max(0.0, h - (2.0 * r))
    if body_h > 0.0:
        renderer.add_rect(f"{key}:body", x, body_y, w, body_h, color, z=z, static=static)
    for i in range(rows):
        yy = float(i) + 0.5
        inset = r - math.sqrt(max(0.0, (r * r) - (yy * yy)))
        seg_x = x + inset
        seg_w = max(0.0, w - (2.0 * inset))
        if seg_w <= 0.0:
            continue
        renderer.add_rect(
            f"{key}:top:{i}",
            seg_x,
            y + float(i),
            seg_w,
            1.0,
            color,
            z=z,
            static=static,
        )
        renderer.add_rect(
            f"{key}:bottom:{i}",
            seg_x,
            y + h - float(i) - 1.0,
            seg_w,
            1.0,
            color,
            z=z,
            static=static,
        )


def _lerp(a: float, b: float, t: float) -> float:
    return a + ((b - a) * t)


def _parse_hex_rgba(raw: str) -> tuple[float, float, float, float]:
    normalized = str(raw).strip().lower()
    if not normalized.startswith("#"):
        return (1.0, 1.0, 1.0, 1.0)
    value = normalized.removeprefix("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value) + "ff"
    elif len(value) == 4:
        value = "".join(ch * 2 for ch in value)
    elif len(value) == 6:
        value = value + "ff"
    if len(value) != 8:
        return (1.0, 1.0, 1.0, 1.0)
    try:
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        a = int(value[6:8], 16)
    except ValueError:
        return (1.0, 1.0, 1.0, 1.0)
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def _format_rgba(rgba: tuple[float, float, float, float]) -> str:
    r = max(0, min(255, int(round(rgba[0] * 255.0))))
    g = max(0, min(255, int(round(rgba[1] * 255.0))))
    b = max(0, min(255, int(round(rgba[2] * 255.0))))
    a = max(0, min(255, int(round(rgba[3] * 255.0))))
    return f"#{r:02x}{g:02x}{b:02x}{a:02x}"


def _add_style_rect(
    renderer: RenderAPI,
    *,
    style_kind: str,
    key: str,
    x: float,
    y: float,
    w: float,
    h: float,
    color: str,
    z: float,
    static: bool,
    radius: float = 0.0,
    thickness: float = 1.0,
    color_secondary: str = "",
    shadow_layers: float = 0.0,
) -> bool:
    add_style_rect = getattr(renderer, "add_style_rect", None)
    if not callable(add_style_rect):
        return False
    add_style_rect(
        style_kind=style_kind,
        key=key,
        x=float(x),
        y=float(y),
        w=float(w),
        h=float(h),
        color=str(color),
        z=float(z),
        static=bool(static),
        radius=float(radius),
        thickness=float(thickness),
        color_secondary=str(color_secondary),
        shadow_layers=float(shadow_layers),
    )
    return True

"""Viewport and resize math helpers for scene rendering."""

from __future__ import annotations


def extract_resize_dimensions(event: dict[str, object]) -> tuple[float | None, float | None]:
    """Extract width/height from heterogeneous resize payloads."""
    width = event.get("width")
    height = event.get("height")
    if isinstance(width, (int, float)) and isinstance(height, (int, float)):
        return float(width), float(height)

    size = event.get("size")
    if isinstance(size, (tuple, list)) and len(size) >= 2:
        w = size[0]
        h = size[1]
        if isinstance(w, (int, float)) and isinstance(h, (int, float)):
            return float(w), float(h)

    logical_size = event.get("logical_size")
    if isinstance(logical_size, (tuple, list)) and len(logical_size) >= 2:
        w = logical_size[0]
        h = logical_size[1]
        if isinstance(w, (int, float)) and isinstance(h, (int, float)):
            return float(w), float(h)
    return None, None


def viewport_transform(
    *,
    width: int,
    height: int,
    design_width: int,
    design_height: int,
    preserve_aspect: bool,
) -> tuple[float, float, float, float]:
    """Return (sx, sy, offset_x, offset_y) from design-space to window-space."""
    if design_width <= 0 or design_height <= 0:
        return 1.0, 1.0, 0.0, 0.0
    raw_sx = float(width) / float(design_width)
    raw_sy = float(height) / float(design_height)
    if not preserve_aspect:
        return raw_sx, raw_sy, 0.0, 0.0
    scale = min(raw_sx, raw_sy)
    viewport_w = float(design_width) * scale
    viewport_h = float(design_height) * scale
    offset_x = (float(width) - viewport_w) * 0.5
    offset_y = (float(height) - viewport_h) * 0.5
    return scale, scale, offset_x, offset_y


def to_design_space(
    *,
    x: float,
    y: float,
    width: int,
    height: int,
    design_width: int,
    design_height: int,
    preserve_aspect: bool,
) -> tuple[float, float]:
    """Convert window-space coordinates to design-space coordinates."""
    sx, sy, ox, oy = viewport_transform(
        width=width,
        height=height,
        design_width=design_width,
        design_height=design_height,
        preserve_aspect=preserve_aspect,
    )
    if sx <= 0.0 or sy <= 0.0:
        return x, y
    return (x - ox) / sx, (y - oy) / sy

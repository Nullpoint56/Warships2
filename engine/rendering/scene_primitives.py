"""Primitive geometry builders for scene rendering."""

from __future__ import annotations

import numpy as np


def grid_positions(
    *, x: float, y: float, width: float, height: float, lines: int, z: float
) -> np.ndarray:
    """Build line-segment positions for an axis-aligned grid."""
    points: list[tuple[float, float, float]] = []
    step_x = width / (lines - 1)
    step_y = height / (lines - 1)
    for idx in range(lines):
        px = x + idx * step_x
        points.append((px, y, z))
        points.append((px, y + height, z))
        py = y + idx * step_y
        points.append((x, py, z))
        points.append((x + width, py, z))
    return np.array(points, dtype=np.float32)

"""Immutable render snapshot contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Vec3:
    """Dimension-neutral position vector."""

    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class Mat4:
    """Dimension-neutral 4x4 transform matrix in row-major order."""

    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.values) != 16:
            raise ValueError("Mat4 must contain exactly 16 values")


IDENTITY_MAT4 = Mat4(
    values=(
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    )
)


@dataclass(frozen=True, slots=True)
class RenderCommand:
    """One immutable draw command in a pass."""

    kind: str
    layer: int = 0
    sort_key: str = ""
    transform: Mat4 = IDENTITY_MAT4
    data: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class RenderPassSnapshot:
    """Immutable render pass payload."""

    name: str
    commands: tuple[RenderCommand, ...] = ()


@dataclass(frozen=True, slots=True)
class RenderSnapshot:
    """Immutable renderer-facing frame snapshot."""

    frame_index: int
    passes: tuple[RenderPassSnapshot, ...] = ()


def create_render_snapshot(
    *,
    frame_index: int,
    passes: tuple[RenderPassSnapshot, ...] = (),
) -> RenderSnapshot:
    """Create a render snapshot value."""
    return RenderSnapshot(frame_index=frame_index, passes=passes)


def mat4_translation(position: Vec3) -> Mat4:
    """Create translation matrix from Vec3 position."""
    return Mat4(
        values=(
            1.0,
            0.0,
            0.0,
            position.x,
            0.0,
            1.0,
            0.0,
            position.y,
            0.0,
            0.0,
            1.0,
            position.z,
            0.0,
            0.0,
            0.0,
            1.0,
        )
    )


def mat4_scale(scale: Vec3) -> Mat4:
    """Create scale matrix from Vec3 scale vector."""
    return Mat4(
        values=(
            scale.x,
            0.0,
            0.0,
            0.0,
            0.0,
            scale.y,
            0.0,
            0.0,
            0.0,
            0.0,
            scale.z,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        )
    )


__all__ = [
    "IDENTITY_MAT4",
    "Mat4",
    "RenderCommand",
    "RenderPassSnapshot",
    "RenderSnapshot",
    "Vec3",
    "mat4_scale",
    "mat4_translation",
    "create_render_snapshot",
]

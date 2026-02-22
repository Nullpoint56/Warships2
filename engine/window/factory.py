"""Window backend selection and factory helpers."""

from __future__ import annotations

from typing import Any

from engine.api.window import WindowPort
from engine.window.rendercanvas_glfw import create_rendercanvas_window


def create_window_layer(
    *,
    width: int,
    height: int,
    title: str,
    update_mode: str,
    min_fps: float,
    max_fps: float,
    vsync: bool,
    backend: str = "rendercanvas_glfw",
) -> WindowPort:
    normalized_backend = _normalize_window_backend(backend)
    if normalized_backend == "rendercanvas_glfw":
        return create_rendercanvas_window(
            width=int(width),
            height=int(height),
            title=title,
            update_mode=update_mode,
            min_fps=float(min_fps),
            max_fps=float(max_fps),
            vsync=bool(vsync),
        )
    if normalized_backend == "direct_glfw":
        raise RuntimeError(
            "ENGINE_WINDOW_BACKEND=direct_glfw is not supported for production runtime: "
            "current renderer surface contract requires a provider exposing get_context('wgpu'). "
            "Use rendercanvas_glfw or complete a direct wgpu/glfw surface integration path."
        )
    raise RuntimeError(f"Unsupported ENGINE_WINDOW_BACKEND: {normalized_backend!r}")


def _normalize_window_backend(raw: str) -> str:
    value = str(raw).strip().lower()
    if value in {"rendercanvas", "rendercanvas_glfw", "glfw"}:
        return "rendercanvas_glfw"
    if value in {"direct_glfw", "glfw_direct"}:
        return "direct_glfw"
    return value


__all__ = ["create_window_layer"]


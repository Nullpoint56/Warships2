"""Window backend selection and factory helpers."""

from __future__ import annotations

import os
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
) -> WindowPort:
    backend = _resolve_window_backend()
    if backend == "rendercanvas_glfw":
        return create_rendercanvas_window(
            width=int(width),
            height=int(height),
            title=title,
            update_mode=update_mode,
            min_fps=float(min_fps),
            max_fps=float(max_fps),
            vsync=bool(vsync),
        )
    if backend == "direct_glfw":
        raise RuntimeError(
            "ENGINE_WINDOW_BACKEND=direct_glfw is not supported for production runtime: "
            "current renderer surface contract requires a provider exposing get_context('wgpu'). "
            "Use rendercanvas_glfw or complete a direct wgpu/glfw surface integration path."
        )
    raise RuntimeError(f"Unsupported ENGINE_WINDOW_BACKEND: {backend!r}")


def _resolve_window_backend() -> str:
    raw = os.getenv("ENGINE_WINDOW_BACKEND", "rendercanvas_glfw")
    value = str(raw).strip().lower()
    if value in {"rendercanvas", "rendercanvas_glfw", "glfw"}:
        return "rendercanvas_glfw"
    if value in {"direct_glfw", "glfw_direct"}:
        return "direct_glfw"
    return value


__all__ = ["create_window_layer"]


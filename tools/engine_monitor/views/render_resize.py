from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.contracts import EventRecord


@dataclass(frozen=True)
class RenderResizeModel:
    resize_events: int
    viewport_updates: int
    camera_projection_updates: int
    pixel_ratio_updates: int
    surface_dim_updates: int
    present_interval_updates: int
    last_resize_value: str


def build_render_resize_model(events: list[EventRecord]) -> RenderResizeModel:
    resize_events = [e for e in events if e.name == "render.resize_event"]
    viewport = [e for e in events if e.name == "render.viewport_applied"]
    camera = [e for e in events if e.name == "render.camera_projection"]
    pixel_ratio = [e for e in events if e.name == "render.pixel_ratio"]
    surface_dims = [e for e in events if e.name == "render.surface_dims"]
    present_interval = [e for e in events if e.name == "render.present_interval"]
    last_resize = resize_events[-1].value if resize_events else None
    return RenderResizeModel(
        resize_events=len(resize_events),
        viewport_updates=len(viewport),
        camera_projection_updates=len(camera),
        pixel_ratio_updates=len(pixel_ratio),
        surface_dim_updates=len(surface_dims),
        present_interval_updates=len(present_interval),
        last_resize_value=str(last_resize) if last_resize is not None else "n/a",
    )

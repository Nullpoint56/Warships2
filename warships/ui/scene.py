"""Scene graph setup for pygfx rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from typing import Callable
from typing import Any
from typing import cast

import numpy as np

try:
    import pygfx as gfx
except Exception as exc:  # pragma: no cover - import guard for environments without graphics deps
    gfx = None
    _gfx_import_error = exc
else:
    _gfx_import_error = None

try:
    import rendercanvas.auto as rc_auto
except Exception as exc:  # pragma: no cover - missing GUI backend
    rc_auto = None
    _canvas_import_error = exc
else:
    _canvas_import_error = None

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SceneRenderer:
    """Minimal 2D renderer wrapper around pygfx."""

    width: int = 1200
    height: int = 720
    design_width: int = 1200
    design_height: int = 720
    preserve_aspect: bool = False
    title: str = "Warships V1"
    _dynamic_nodes: list[object] = field(default_factory=list)
    _rect_nodes: dict[str, Any] = field(default_factory=dict)
    _line_nodes: dict[str, Any] = field(default_factory=dict)
    _text_nodes: dict[str, Any] = field(default_factory=dict)
    _rect_props: dict[str, tuple[float, float, float, float, str, float]] = field(default_factory=dict)
    _text_props: dict[str, tuple[str, float, float, float, str, str, float]] = field(default_factory=dict)
    _static_rect_keys: set[str] = field(default_factory=set)
    _static_line_keys: set[str] = field(default_factory=set)
    _static_text_keys: set[str] = field(default_factory=set)
    _active_rect_keys: set[str] = field(default_factory=set)
    _active_line_keys: set[str] = field(default_factory=set)
    _active_text_keys: set[str] = field(default_factory=set)
    canvas: Any = field(init=False)
    renderer: Any = field(init=False)
    scene: Any = field(init=False)
    camera: Any = field(init=False)
    _draw_failed: bool = field(init=False, default=False)
    _is_closed: bool = field(init=False, default=False)
    _draw_callback: Callable[[], None] | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if gfx is None:
            raise RuntimeError(
                f"pygfx dependency unavailable: {_gfx_import_error!r}. Install 'pygfx' and 'wgpu'."
            )
        if rc_auto is None:
            raise RuntimeError(
                "Render canvas backend unavailable. Install a desktop backend such as 'glfw' or 'pyside6'. "
                f"Original error: {_canvas_import_error!r}"
            )

        canvas_cls = getattr(rc_auto, "RenderCanvas", None)
        if canvas_cls is None:
            raise RuntimeError("rendercanvas.auto did not expose RenderCanvas.")

        self.canvas = canvas_cls(size=(self.width, self.height), title=self.title)
        aspect_mode = os.getenv("WARSHIPS_UI_ASPECT_MODE", "contain").strip().lower()
        self.preserve_aspect = aspect_mode in {"contain", "preserve", "fixed"}
        window_mode = os.getenv("WARSHIPS_WINDOW_MODE", "fullscreen").strip().lower()
        if window_mode in {"fullscreen", "borderless", "maximized"}:
            self._apply_startup_window_mode(window_mode)
        self.renderer = gfx.WgpuRenderer(self.canvas)
        self.scene = gfx.Scene()
        self.camera = gfx.OrthographicCamera(self.width, self.height)
        self._update_camera_projection()
        self._bind_resize_events()
        self._sync_size_from_canvas()

    def _bind_resize_events(self) -> None:
        add_handler = getattr(self.canvas, "add_event_handler", None)
        if not callable(add_handler):
            return
        try:
            add_handler(self._on_resize, "resize")
        except Exception:
            logger.debug("resize_event_binding_failed", exc_info=True)

    def _on_resize(self, event: object) -> None:
        if not isinstance(event, dict):
            self._sync_size_from_canvas()
            return
        width, height = self._extract_resize_dimensions(event)
        if width is None or height is None:
            self._sync_size_from_canvas()
            return
        self._apply_canvas_size(width, height)

    @staticmethod
    def _extract_resize_dimensions(event: dict[str, object]) -> tuple[float | None, float | None]:
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

    def _apply_canvas_size(self, width: float, height: float) -> bool:
        if width <= 1.0 or height <= 1.0:
            return False
        new_width = int(width)
        new_height = int(height)
        if new_width == self.width and new_height == self.height:
            return False
        self.width = new_width
        self.height = new_height
        self._update_camera_projection()
        return True

    def _update_camera_projection(self) -> None:
        if hasattr(self.camera, "width"):
            self.camera.width = self.width
        if hasattr(self.camera, "height"):
            self.camera.height = self.height
        self.camera.local.position = (self.width / 2.0, self.height / 2.0, 0.0)
        self.camera.local.scale_y = -1.0

    def _apply_startup_window_mode(self, window_mode: str) -> None:
        """Set startup window mode for GLFW backend."""
        try:
            import rendercanvas.glfw as rc_glfw  # type: ignore
        except Exception:
            return
        window = getattr(self.canvas, "_window", None)
        if window is None:
            return
        glfw = rc_glfw.glfw
        try:
            glfw.set_window_attrib(window, glfw.RESIZABLE, glfw.FALSE)
        except Exception:
            pass
        if window_mode == "maximized":
            try:
                glfw.maximize_window(window)
            except Exception:
                pass
            return
        monitor = glfw.get_primary_monitor()
        if not monitor:
            try:
                glfw.maximize_window(window)
            except Exception:
                pass
            return
        if window_mode == "fullscreen":
            video_mode = glfw.get_video_mode(monitor)
            if video_mode is not None:
                try:
                    glfw.set_window_monitor(
                        window,
                        monitor,
                        0,
                        0,
                        int(video_mode.size.width),
                        int(video_mode.size.height),
                        int(video_mode.refresh_rate),
                    )
                    return
                except Exception:
                    pass
        try:
            x, y, w, h = glfw.get_monitor_workarea(monitor)
            glfw.set_window_monitor(window, None, int(x), int(y), int(w), int(h), 0)
        except Exception:
            try:
                glfw.maximize_window(window)
            except Exception:
                pass

    def _sync_size_from_canvas(self) -> bool:
        get_logical_size = getattr(self.canvas, "get_logical_size", None)
        if not callable(get_logical_size):
            return False
        try:
            size = get_logical_size()
        except Exception:
            return False
        if not (isinstance(size, (tuple, list)) and len(size) >= 2):
            return False
        width, height = size[0], size[1]
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            return False
        return self._apply_canvas_size(float(width), float(height))

    def begin_frame(self) -> None:
        """Start a frame and reset active key trackers."""
        self._active_rect_keys.clear()
        self._active_line_keys.clear()
        self._active_text_keys.clear()

    def _scale_x(self) -> float:
        sx, _, _, _ = self._viewport_transform()
        return sx

    def _scale_y(self) -> float:
        _, sy, _, _ = self._viewport_transform()
        return sy

    def _viewport_transform(self) -> tuple[float, float, float, float]:
        """Return (sx, sy, offset_x, offset_y) from design-space to window-space."""
        if self.design_width <= 0 or self.design_height <= 0:
            return 1.0, 1.0, 0.0, 0.0
        raw_sx = float(self.width) / float(self.design_width)
        raw_sy = float(self.height) / float(self.design_height)
        if not self.preserve_aspect:
            return raw_sx, raw_sy, 0.0, 0.0
        scale = min(raw_sx, raw_sy)
        viewport_w = float(self.design_width) * scale
        viewport_h = float(self.design_height) * scale
        offset_x = (float(self.width) - viewport_w) * 0.5
        offset_y = (float(self.height) - viewport_h) * 0.5
        return scale, scale, offset_x, offset_y

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        """Convert window-space coordinates to design-space coordinates."""
        sx = self._scale_x()
        sy = self._scale_y()
        _, _, ox, oy = self._viewport_transform()
        if sx <= 0.0 or sy <= 0.0:
            return x, y
        dx = (x - ox) / sx
        dy = (y - oy) / sy
        return dx, dy

    def end_frame(self) -> None:
        """Hide dynamic retained nodes that were not touched this frame."""
        for key, node in self._rect_nodes.items():
            if key in self._static_rect_keys:
                continue
            if key not in self._active_rect_keys:
                node.visible = False
        for key, node in self._line_nodes.items():
            if key in self._static_line_keys:
                continue
            if key not in self._active_line_keys:
                node.visible = False
        for key, node in self._text_nodes.items():
            if key in self._static_text_keys:
                continue
            if key not in self._active_text_keys:
                node.visible = False

    def clear_dynamic(self) -> None:
        """Compatibility wrapper for older call-sites."""
        self.begin_frame()
        self.end_frame()

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
        """Add a filled rectangle."""
        color_value = cast(Any, color)
        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = w * sx
        th = h * sy
        if key is not None and key in self._rect_nodes:
            node = self._rect_nodes[key]
            new_props = (x, y, w, h, color, z)
            if self._rect_props.get(key) != new_props:
                node.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
                if hasattr(node, "material"):
                    node.material.color = color_value
                self._rect_props[key] = new_props
            node.visible = True
            if static:
                self._static_rect_keys.add(key)
            else:
                self._active_rect_keys.add(key)
            return

        mesh = gfx.Mesh(gfx.plane_geometry(tw, th), gfx.MeshBasicMaterial(color=color))
        mesh.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
        self.scene.add(mesh)
        if key is None:
            self._dynamic_nodes.append(mesh)
        else:
            self._rect_nodes[key] = mesh
            self._rect_props[key] = (x, y, w, h, color, z)
            if static:
                self._static_rect_keys.add(key)
            else:
                self._active_rect_keys.add(key)

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
        """Add a batched line-segment grid."""
        if key in self._line_nodes:
            node = self._line_nodes[key]
            node.visible = True
            if static:
                self._static_line_keys.add(key)
            else:
                self._active_line_keys.add(key)
            return

        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = width * sx
        th = height * sy
        points: list[tuple[float, float, float]] = []
        step_x = tw / (lines - 1)
        step_y = th / (lines - 1)
        for idx in range(lines):
            px = tx + idx * step_x
            points.append((px, ty, z))
            points.append((px, ty + th, z))
            py = ty + idx * step_y
            points.append((tx, py, z))
            points.append((tx + tw, py, z))

        positions = np.array(points, dtype=np.float32)
        geometry = gfx.Geometry(positions=positions)
        material = gfx.LineSegmentMaterial(color=cast(Any, color), thickness=1.0, thickness_space="screen")
        line = gfx.Line(geometry, material)
        self.scene.add(line)
        self._line_nodes[key] = line
        if static:
            self._static_line_keys.add(key)
        else:
            self._active_line_keys.add(key)

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
        """Add screen-space text."""
        color_value = cast(Any, color)
        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tsize = font_size * min(sx, sy)
        if key is not None and key in self._text_nodes:
            node = self._text_nodes[key]
            new_props = (text, x, y, font_size, color, anchor, z)
            if self._text_props.get(key) != new_props:
                node.set_text(text)
                node.local.position = (tx, ty, z)
                if hasattr(node, "font_size"):
                    node.font_size = tsize
                if hasattr(node, "material"):
                    node.material.color = color_value
                self._text_props[key] = new_props
            node.visible = True
            if static:
                self._static_text_keys.add(key)
            else:
                self._active_text_keys.add(key)
            return

        node = gfx.Text(
            text=text,
            font_size=tsize,
            screen_space=True,
            anchor=anchor,
            material=gfx.TextMaterial(color=color_value),
        )
        node.local.position = (tx, ty, z)
        self.scene.add(node)
        if key is None:
            self._dynamic_nodes.append(node)
        else:
            self._text_nodes[key] = node
            self._text_props[key] = (text, x, y, font_size, color, anchor, z)
            if static:
                self._static_text_keys.add(key)
            else:
                self._active_text_keys.add(key)

    def set_title(self, title: str) -> None:
        """Set window title when supported by backend."""
        self.title = title
        if hasattr(self.canvas, "set_title"):
            self.canvas.set_title(title)

    def invalidate(self) -> None:
        """Schedule one redraw."""
        if self._is_closed:
            return
        if hasattr(self.canvas, "request_draw"):
            self.canvas.request_draw()

    def run(self, draw_callback: Callable[[], None]) -> None:
        """Start draw loop."""
        self._draw_callback = draw_callback

        def _draw_frame() -> None:
            if self._draw_failed or self._is_closed:
                return
            try:
                self._sync_size_from_canvas()
                if self._draw_callback is None:
                    return
                self._draw_callback()
                if self._is_closed:
                    return
                self.renderer.render(self.scene, self.camera)
            except Exception:  # pylint: disable=broad-exception-caught
                self._draw_failed = True
                logger.exception("unhandled_exception_in_draw_loop")
                self.close()

        self.canvas.request_draw(_draw_frame)
        self.invalidate()
        loop = getattr(rc_auto, "loop", None)
        if loop is not None and hasattr(loop, "run"):
            loop.run()
            return
        run_func = getattr(rc_auto, "run", None)
        if callable(run_func):
            run_func()
            return
        raise RuntimeError("rendercanvas.auto did not expose a runnable loop.")

    def close(self) -> None:
        """Close canvas and stop backend loop when possible."""
        if self._is_closed:
            return
        self._is_closed = True
        if hasattr(self.canvas, "close"):
            self.canvas.close()
        loop = getattr(rc_auto, "loop", None)
        if loop is not None and hasattr(loop, "stop"):
            loop.stop()

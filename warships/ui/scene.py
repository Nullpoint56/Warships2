"""Scene graph setup for pygfx rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
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
        self.renderer = gfx.WgpuRenderer(self.canvas)
        self.scene = gfx.Scene()
        self.camera = gfx.OrthographicCamera(self.width, self.height)
        self.camera.local.position = (self.width / 2.0, self.height / 2.0, 0.0)
        self.camera.local.scale_y = -1.0

    def begin_frame(self) -> None:
        """Start a frame and reset active key trackers."""
        self._active_rect_keys.clear()
        self._active_line_keys.clear()
        self._active_text_keys.clear()

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
        if key is not None and key in self._rect_nodes:
            node = self._rect_nodes[key]
            new_props = (x, y, w, h, color, z)
            if self._rect_props.get(key) != new_props:
                node.local.position = (x + w / 2.0, y + h / 2.0, z)
                if hasattr(node, "material"):
                    node.material.color = color_value
                self._rect_props[key] = new_props
            node.visible = True
            if static:
                self._static_rect_keys.add(key)
            else:
                self._active_rect_keys.add(key)
            return

        mesh = gfx.Mesh(gfx.plane_geometry(w, h), gfx.MeshBasicMaterial(color=color))
        mesh.local.position = (x + w / 2.0, y + h / 2.0, z)
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
        if key is not None and key in self._text_nodes:
            node = self._text_nodes[key]
            new_props = (text, x, y, font_size, color, anchor, z)
            if self._text_props.get(key) != new_props:
                node.set_text(text)
                node.local.position = (x, y, z)
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
            font_size=font_size,
            screen_space=True,
            anchor=anchor,
            material=gfx.TextMaterial(color=color_value),
        )
        node.local.position = (x, y, z)
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

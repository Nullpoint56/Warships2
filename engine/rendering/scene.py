"""Scene graph setup for pygfx rendering."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, cast

from engine.rendering.scene_retained import (
    hide_inactive_nodes,
    upsert_grid,
    upsert_rect,
    upsert_text,
)
from engine.rendering.scene_runtime import (
    get_canvas_logical_size,
    resolve_preserve_aspect,
    run_backend_loop,
    stop_backend_loop,
)
from engine.rendering.scene_viewport import (
    extract_resize_dimensions,
    to_design_space,
    viewport_transform,
)

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
    try:
        # Guard against transient zero-size events (e.g. snap/resize on Windows) before they
        # propagate into rendercanvas internals.
        from rendercanvas import _size as _rc_size  # type: ignore

        if not getattr(_rc_size.SizeInfo.set_physical_size, "_warships_size_clamped", False):
            _orig_set_physical_size = _rc_size.SizeInfo.set_physical_size

            def _safe_set_physical_size(
                self: object, width: int, height: int, pixel_ratio: float
            ) -> None:
                _orig_set_physical_size(self, max(1, int(width)), max(1, int(height)), pixel_ratio)

            _safe_set_physical_size._warships_size_clamped = True  # type: ignore[attr-defined]
            _rc_size.SizeInfo.set_physical_size = _safe_set_physical_size  # type: ignore
    except Exception:
        pass

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
    _rect_props: dict[str, tuple[float, float, float, float, str, float]] = field(
        default_factory=dict
    )
    _line_props: dict[str, tuple[float, float, float, float, int, str, float]] = field(
        default_factory=dict
    )
    _text_props: dict[str, tuple[str, float, float, float, str, str, float]] = field(
        default_factory=dict
    )
    _rect_viewport_rev: dict[str, int] = field(default_factory=dict)
    _line_viewport_rev: dict[str, int] = field(default_factory=dict)
    _text_viewport_rev: dict[str, int] = field(default_factory=dict)
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
    _viewport_revision: int = field(init=False, default=0)

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
        self.preserve_aspect = resolve_preserve_aspect()
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
        width, height = extract_resize_dimensions(event)
        if width is None or height is None:
            self._sync_size_from_canvas()
            return
        self._apply_canvas_size(width, height)

    def _apply_canvas_size(self, width: float, height: float) -> bool:
        if width <= 1.0 or height <= 1.0:
            return False
        new_width = int(width)
        new_height = int(height)
        if new_width == self.width and new_height == self.height:
            return False
        self.width = new_width
        self.height = new_height
        self._viewport_revision += 1
        self._update_camera_projection()
        return True

    def _update_camera_projection(self) -> None:
        if hasattr(self.camera, "width"):
            self.camera.width = self.width
        if hasattr(self.camera, "height"):
            self.camera.height = self.height
        self.camera.local.position = (self.width / 2.0, self.height / 2.0, 0.0)
        self.camera.local.scale_y = -1.0

    def _sync_size_from_canvas(self) -> bool:
        size = get_canvas_logical_size(self.canvas)
        if size is None:
            return False
        width, height = size
        return self._apply_canvas_size(width, height)

    def begin_frame(self) -> None:
        """Start a frame and reset active key trackers."""
        self._active_rect_keys.clear()
        self._active_line_keys.clear()
        self._active_text_keys.clear()

    def _viewport_transform(self) -> tuple[float, float, float, float]:
        return viewport_transform(
            width=self.width,
            height=self.height,
            design_width=self.design_width,
            design_height=self.design_height,
            preserve_aspect=self.preserve_aspect,
        )

    def to_design_space(self, x: float, y: float) -> tuple[float, float]:
        return to_design_space(
            x=x,
            y=y,
            width=self.width,
            height=self.height,
            design_width=self.design_width,
            design_height=self.design_height,
            preserve_aspect=self.preserve_aspect,
        )

    def end_frame(self) -> None:
        """Hide dynamic retained nodes that were not touched this frame."""
        hide_inactive_nodes(self._rect_nodes, self._static_rect_keys, self._active_rect_keys)
        hide_inactive_nodes(self._line_nodes, self._static_line_keys, self._active_line_keys)
        hide_inactive_nodes(self._text_nodes, self._static_text_keys, self._active_text_keys)

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
        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = w * sx
        th = h * sy
        upsert_rect(
            gfx=gfx,
            scene=self.scene,
            key=key,
            x=x,
            y=y,
            w=w,
            h=h,
            color=color,
            z=z,
            tx=tx,
            ty=ty,
            tw=tw,
            th=th,
            viewport_revision=self._viewport_revision,
            rect_nodes=self._rect_nodes,
            rect_props=self._rect_props,
            rect_viewport_rev=self._rect_viewport_rev,
            static_rect_keys=self._static_rect_keys,
            active_rect_keys=self._active_rect_keys,
            dynamic_nodes=self._dynamic_nodes,
            static=static,
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
        """Add a batched line-segment grid."""
        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tw = width * sx
        th = height * sy
        upsert_grid(
            gfx=gfx,
            scene=self.scene,
            key=key,
            x=x,
            y=y,
            width=width,
            height=height,
            lines=lines,
            color=color,
            z=z,
            tx=tx,
            ty=ty,
            tw=tw,
            th=th,
            viewport_revision=self._viewport_revision,
            line_nodes=self._line_nodes,
            line_props=self._line_props,
            line_viewport_rev=self._line_viewport_rev,
            static_line_keys=self._static_line_keys,
            active_line_keys=self._active_line_keys,
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
        """Add screen-space text."""
        sx, sy, ox, oy = self._viewport_transform()
        tx = x * sx + ox
        ty = y * sy + oy
        tsize = font_size * min(sx, sy)
        upsert_text(
            gfx=gfx,
            scene=self.scene,
            key=key,
            text=text,
            x=x,
            y=y,
            font_size=font_size,
            color=color,
            anchor=anchor,
            z=z,
            tx=tx,
            ty=ty,
            tsize=tsize,
            viewport_revision=self._viewport_revision,
            text_nodes=self._text_nodes,
            text_props=self._text_props,
            text_viewport_rev=self._text_viewport_rev,
            static_text_keys=self._static_text_keys,
            active_text_keys=self._active_text_keys,
            dynamic_nodes=self._dynamic_nodes,
            static=static,
        )

    def fill_window(self, key: str, color: str, z: float = -100.0) -> None:
        """Fill the entire window in window-space coordinates."""
        color_value = cast(Any, color)
        tw = float(self.width)
        th = float(self.height)
        tx = 0.0
        ty = 0.0
        if key in self._rect_nodes:
            node = self._rect_nodes[key]
            new_props = (tx, ty, tw, th, color, z)
            needs_update = (
                self._rect_props.get(key) != new_props
                or self._rect_viewport_rev.get(key, -1) != self._viewport_revision
            )
            if needs_update:
                node.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
                node.geometry = gfx.plane_geometry(tw, th)
                if hasattr(node, "material"):
                    node.material.color = color_value
                self._rect_props[key] = new_props
                self._rect_viewport_rev[key] = self._viewport_revision
            node.visible = True
            self._active_rect_keys.add(key)
            return

        mesh = gfx.Mesh(gfx.plane_geometry(tw, th), gfx.MeshBasicMaterial(color=color))
        mesh.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
        self.scene.add(mesh)
        self._rect_nodes[key] = mesh
        self._rect_props[key] = (tx, ty, tw, th, color, z)
        self._rect_viewport_rev[key] = self._viewport_revision
        self._active_rect_keys.add(key)

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
        run_backend_loop(rc_auto)

    def close(self) -> None:
        """Close canvas and stop backend loop when possible."""
        if self._is_closed:
            return
        self._is_closed = True
        if hasattr(self.canvas, "close"):
            self.canvas.close()
        stop_backend_loop(rc_auto)

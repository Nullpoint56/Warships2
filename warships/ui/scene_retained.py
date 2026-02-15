"""Retained-node cache/update operations for SceneRenderer."""

from __future__ import annotations

from typing import Any
from typing import cast

from warships.ui.scene_primitives import grid_positions


def hide_inactive_nodes(nodes: dict[str, Any], static_keys: set[str], active_keys: set[str]) -> None:
    """Hide retained nodes that were not touched this frame."""
    for key, node in nodes.items():
        if key in static_keys:
            continue
        if key not in active_keys:
            node.visible = False


def upsert_rect(
    *,
    gfx: Any,
    scene: Any,
    key: str | None,
    x: float,
    y: float,
    w: float,
    h: float,
    color: str,
    z: float,
    tx: float,
    ty: float,
    tw: float,
    th: float,
    viewport_revision: int,
    rect_nodes: dict[str, Any],
    rect_props: dict[str, tuple[float, float, float, float, str, float]],
    rect_viewport_rev: dict[str, int],
    static_rect_keys: set[str],
    active_rect_keys: set[str],
    dynamic_nodes: list[Any],
    static: bool,
) -> None:
    """Create or update retained rectangle node."""
    color_value = cast(Any, color)
    if key is not None and key in rect_nodes:
        node = rect_nodes[key]
        new_props = (x, y, w, h, color, z)
        needs_update = rect_props.get(key) != new_props or rect_viewport_rev.get(key, -1) != viewport_revision
        if needs_update:
            node.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
            node.geometry = gfx.plane_geometry(tw, th)
            if hasattr(node, "material"):
                node.material.color = color_value
            rect_props[key] = new_props
            rect_viewport_rev[key] = viewport_revision
        node.visible = True
        if static:
            static_rect_keys.add(key)
        else:
            active_rect_keys.add(key)
        return

    mesh = gfx.Mesh(gfx.plane_geometry(tw, th), gfx.MeshBasicMaterial(color=color))
    mesh.local.position = (tx + tw / 2.0, ty + th / 2.0, z)
    scene.add(mesh)
    if key is None:
        dynamic_nodes.append(mesh)
    else:
        rect_nodes[key] = mesh
        rect_props[key] = (x, y, w, h, color, z)
        rect_viewport_rev[key] = viewport_revision
        if static:
            static_rect_keys.add(key)
        else:
            active_rect_keys.add(key)


def upsert_grid(
    *,
    gfx: Any,
    scene: Any,
    key: str,
    x: float,
    y: float,
    width: float,
    height: float,
    lines: int,
    color: str,
    z: float,
    tx: float,
    ty: float,
    tw: float,
    th: float,
    viewport_revision: int,
    line_nodes: dict[str, Any],
    line_props: dict[str, tuple[float, float, float, float, int, str, float]],
    line_viewport_rev: dict[str, int],
    static_line_keys: set[str],
    active_line_keys: set[str],
    static: bool,
) -> None:
    """Create or update retained grid line node."""
    new_props = (x, y, width, height, lines, color, z)
    if key in line_nodes:
        node = line_nodes[key]
        needs_update = line_props.get(key) != new_props or line_viewport_rev.get(key, -1) != viewport_revision
        if needs_update:
            positions = grid_positions(x=tx, y=ty, width=tw, height=th, lines=lines, z=z)
            node.geometry = gfx.Geometry(positions=positions)
            if hasattr(node, "material"):
                node.material.color = cast(Any, color)
            line_props[key] = new_props
            line_viewport_rev[key] = viewport_revision
        node.visible = True
        if static:
            static_line_keys.add(key)
        else:
            active_line_keys.add(key)
        return

    positions = grid_positions(x=tx, y=ty, width=tw, height=th, lines=lines, z=z)
    geometry = gfx.Geometry(positions=positions)
    material = gfx.LineSegmentMaterial(color=cast(Any, color), thickness=1.0, thickness_space="screen")
    line = gfx.Line(geometry, material)
    scene.add(line)
    line_nodes[key] = line
    line_props[key] = new_props
    line_viewport_rev[key] = viewport_revision
    if static:
        static_line_keys.add(key)
    else:
        active_line_keys.add(key)


def upsert_text(
    *,
    gfx: Any,
    scene: Any,
    key: str | None,
    text: str,
    x: float,
    y: float,
    font_size: float,
    color: str,
    anchor: str,
    z: float,
    tx: float,
    ty: float,
    tsize: float,
    viewport_revision: int,
    text_nodes: dict[str, Any],
    text_props: dict[str, tuple[str, float, float, float, str, str, float]],
    text_viewport_rev: dict[str, int],
    static_text_keys: set[str],
    active_text_keys: set[str],
    dynamic_nodes: list[Any],
    static: bool,
) -> None:
    """Create or update retained text node."""
    color_value = cast(Any, color)
    if key is not None and key in text_nodes:
        node = text_nodes[key]
        new_props = (text, x, y, font_size, color, anchor, z)
        needs_update = text_props.get(key) != new_props or text_viewport_rev.get(key, -1) != viewport_revision
        if needs_update:
            node.set_text(text)
            node.local.position = (tx, ty, z)
            if hasattr(node, "font_size"):
                node.font_size = tsize
            if hasattr(node, "material"):
                node.material.color = color_value
            text_props[key] = new_props
            text_viewport_rev[key] = viewport_revision
        node.visible = True
        if static:
            static_text_keys.add(key)
        else:
            active_text_keys.add(key)
        return

    node = gfx.Text(
        text=text,
        font_size=tsize,
        screen_space=True,
        anchor=anchor,
        material=gfx.TextMaterial(color=color_value),
    )
    node.local.position = (tx, ty, z)
    scene.add(node)
    if key is None:
        dynamic_nodes.append(node)
    else:
        text_nodes[key] = node
        text_props[key] = (text, x, y, font_size, color, anchor, z)
        text_viewport_rev[key] = viewport_revision
        if static:
            static_text_keys.add(key)
        else:
            active_text_keys.add(key)


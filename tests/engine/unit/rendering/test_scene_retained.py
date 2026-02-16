from __future__ import annotations

from types import SimpleNamespace

from engine.rendering.scene_retained import hide_inactive_nodes, upsert_grid, upsert_rect, upsert_text


class _MeshBasicMaterial:
    def __init__(self, color) -> None:
        self.color = color


class _Mesh:
    def __init__(self, geometry, material) -> None:
        self.geometry = geometry
        self.material = material
        self.local = SimpleNamespace(position=(0.0, 0.0, 0.0))
        self.visible = True


class _Geometry:
    def __init__(self, positions=None) -> None:
        self.positions = positions


class _LineSegmentMaterial:
    def __init__(self, color, thickness, thickness_space) -> None:
        self.color = color
        self.thickness = thickness
        self.thickness_space = thickness_space


class _Line:
    def __init__(self, geometry, material) -> None:
        self.geometry = geometry
        self.material = material
        self.visible = True


class _TextMaterial:
    def __init__(self, color) -> None:
        self.color = color


class _Text:
    def __init__(self, text, font_size, screen_space, anchor, material) -> None:
        self.text = text
        self.font_size = font_size
        self.screen_space = screen_space
        self.anchor = anchor
        self.material = material
        self.local = SimpleNamespace(position=(0.0, 0.0, 0.0))
        self.visible = True

    def set_text(self, value: str) -> None:
        self.text = value


class _Gfx:
    Mesh = _Mesh
    MeshBasicMaterial = _MeshBasicMaterial
    Geometry = _Geometry
    LineSegmentMaterial = _LineSegmentMaterial
    Line = _Line
    TextMaterial = _TextMaterial
    Text = _Text

    @staticmethod
    def plane_geometry(w, h):
        return ("plane", w, h)


class _Scene:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, node) -> None:
        self.added.append(node)


def test_hide_inactive_nodes_hides_non_static_missing_keys() -> None:
    active = {"a"}
    static = {"s"}
    nodes = {"a": SimpleNamespace(visible=True), "b": SimpleNamespace(visible=True), "s": SimpleNamespace(visible=True)}
    hide_inactive_nodes(nodes, static, active)
    assert nodes["a"].visible
    assert not nodes["b"].visible
    assert nodes["s"].visible


def test_upsert_rect_create_and_update() -> None:
    scene = _Scene()
    rect_nodes: dict[str, object] = {}
    rect_props: dict[str, tuple[float, float, float, float, str, float]] = {}
    rect_viewport_rev: dict[str, int] = {}
    static_rect_keys: set[str] = set()
    active_rect_keys: set[str] = set()
    dynamic_nodes: list[object] = []

    upsert_rect(
        gfx=_Gfx,
        scene=scene,
        key="k",
        x=1,
        y=2,
        w=3,
        h=4,
        color="#fff",
        z=1.0,
        tx=10,
        ty=20,
        tw=30,
        th=40,
        viewport_revision=1,
        rect_nodes=rect_nodes,
        rect_props=rect_props,
        rect_viewport_rev=rect_viewport_rev,
        static_rect_keys=static_rect_keys,
        active_rect_keys=active_rect_keys,
        dynamic_nodes=dynamic_nodes,
        static=False,
    )
    assert "k" in rect_nodes
    assert len(scene.added) == 1
    assert "k" in active_rect_keys

    node = rect_nodes["k"]
    upsert_rect(
        gfx=_Gfx,
        scene=scene,
        key="k",
        x=1,
        y=2,
        w=3,
        h=4,
        color="#0ff",
        z=1.0,
        tx=10,
        ty=20,
        tw=30,
        th=40,
        viewport_revision=2,
        rect_nodes=rect_nodes,
        rect_props=rect_props,
        rect_viewport_rev=rect_viewport_rev,
        static_rect_keys=static_rect_keys,
        active_rect_keys=active_rect_keys,
        dynamic_nodes=dynamic_nodes,
        static=False,
    )
    assert rect_nodes["k"] is node
    assert rect_props["k"] == (1, 2, 3, 4, "#0ff", 1.0)


def test_upsert_grid_create_and_update() -> None:
    scene = _Scene()
    line_nodes: dict[str, object] = {}
    line_props: dict[str, tuple[float, float, float, float, int, str, float]] = {}
    line_viewport_rev: dict[str, int] = {}
    static_line_keys: set[str] = set()
    active_line_keys: set[str] = set()

    upsert_grid(
        gfx=_Gfx,
        scene=scene,
        key="g",
        x=0,
        y=0,
        width=10,
        height=10,
        lines=3,
        color="#fff",
        z=0.1,
        tx=0,
        ty=0,
        tw=10,
        th=10,
        viewport_revision=1,
        line_nodes=line_nodes,
        line_props=line_props,
        line_viewport_rev=line_viewport_rev,
        static_line_keys=static_line_keys,
        active_line_keys=active_line_keys,
        static=False,
    )
    assert "g" in line_nodes
    assert len(scene.added) == 1
    assert line_props["g"] == (0, 0, 10, 10, 3, "#fff", 0.1)
    node = line_nodes["g"]

    upsert_grid(
        gfx=_Gfx,
        scene=scene,
        key="g",
        x=0,
        y=0,
        width=12,
        height=10,
        lines=4,
        color="#0ff",
        z=0.2,
        tx=0,
        ty=0,
        tw=12,
        th=10,
        viewport_revision=2,
        line_nodes=line_nodes,
        line_props=line_props,
        line_viewport_rev=line_viewport_rev,
        static_line_keys=static_line_keys,
        active_line_keys=active_line_keys,
        static=False,
    )
    assert line_nodes["g"] is node
    assert line_props["g"] == (0, 0, 12, 10, 4, "#0ff", 0.2)


def test_upsert_text_create_and_update() -> None:
    scene = _Scene()
    text_nodes: dict[str, object] = {}
    text_props: dict[str, tuple[str, float, float, float, str, str, float]] = {}
    text_viewport_rev: dict[str, int] = {}
    static_text_keys: set[str] = set()
    active_text_keys: set[str] = set()
    dynamic_nodes: list[object] = []

    upsert_text(
        gfx=_Gfx,
        scene=scene,
        key="t",
        text="hello",
        x=1,
        y=2,
        font_size=12,
        color="#fff",
        anchor="top-left",
        z=2,
        tx=10,
        ty=20,
        tsize=14,
        viewport_revision=1,
        text_nodes=text_nodes,
        text_props=text_props,
        text_viewport_rev=text_viewport_rev,
        static_text_keys=static_text_keys,
        active_text_keys=active_text_keys,
        dynamic_nodes=dynamic_nodes,
        static=False,
    )
    assert "t" in text_nodes
    assert len(scene.added) == 1
    node = text_nodes["t"]

    upsert_text(
        gfx=_Gfx,
        scene=scene,
        key="t",
        text="world",
        x=1,
        y=2,
        font_size=12,
        color="#0ff",
        anchor="middle-center",
        z=3,
        tx=10,
        ty=20,
        tsize=16,
        viewport_revision=2,
        text_nodes=text_nodes,
        text_props=text_props,
        text_viewport_rev=text_viewport_rev,
        static_text_keys=static_text_keys,
        active_text_keys=active_text_keys,
        dynamic_nodes=dynamic_nodes,
        static=False,
    )
    assert text_nodes["t"] is node
    assert node.text == "world"
    assert text_props["t"] == ("world", 1, 2, 12, "#0ff", "middle-center", 3)

from __future__ import annotations

from pathlib import Path


def test_no_pygfx_imports_in_active_runtime_rendering_path() -> None:
    root = Path(__file__).resolve().parents[4]
    legacy_renderer_files = (
        root / "engine/rendering/scene.py",
        root / "engine/rendering/scene_retained.py",
        root / "engine/rendering/scene_primitives.py",
    )
    for file_path in legacy_renderer_files:
        assert not file_path.exists()

    runtime_render_files = (
        root / "engine/rendering/__init__.py",
        root / "engine/rendering/wgpu_renderer.py",
        root / "engine/runtime/bootstrap.py",
        root / "engine/runtime/window_frontend.py",
        root / "engine/runtime/host.py",
    )
    for file_path in runtime_render_files:
        text = file_path.read_text(encoding="utf-8")
        assert "import pygfx" not in text
        assert "from pygfx" not in text

from __future__ import annotations

from engine.runtime.host import EngineHost


def test_runtime_metadata_versions_are_backend_agnostic() -> None:
    metadata = EngineHost._runtime_metadata()  # noqa: SLF001
    versions = metadata.get("engine_versions", {})

    assert isinstance(versions, dict)
    assert "wgpu" in versions
    assert "rendercanvas" in versions
    assert "pygfx" not in versions

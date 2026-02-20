from __future__ import annotations

from pathlib import Path


def test_no_pygfx_dependency_or_runtime_imports_or_active_doc_mentions() -> None:
    root = Path(__file__).resolve().parents[4]

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "pygfx>=" not in pyproject
    assert '"pygfx.*"' not in pyproject

    for code_root in (root / "engine", root / "warships"):
        for file_path in code_root.rglob("*.py"):
            text = file_path.read_text(encoding="utf-8")
            assert "import pygfx" not in text
            assert "from pygfx" not in text

    active_docs = (
        root / "docs/architecture/system_overview.md",
        root / "docs/operations/windows_build.md",
        root / "docs/operations/runtime_configuration.md",
    )
    for file_path in active_docs:
        text = file_path.read_text(encoding="utf-8").lower()
        assert "pygfx" not in text

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def _iter_python_files(base: Path) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _collect_import_targets(path: Path, *, top_level_only: bool) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = tree.body if top_level_only else list(ast.walk(tree))
    targets: list[str] = []
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            targets.append(node.module)
    return targets


def _collect_wildcard_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wildcards: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if any(alias.name == "*" for alias in node.names):
            module = node.module or "<relative>"
            wildcards.append(module)
    return wildcards


def test_engine_package_does_not_import_warships() -> None:
    violations: list[str] = []
    for path in _iter_python_files(REPO_ROOT / "engine"):
        for target in _collect_import_targets(path, top_level_only=False):
            if target == "warships" or target.startswith("warships."):
                violations.append(f"{path.relative_to(REPO_ROOT)} -> {target}")
    assert not violations, "Engine must not import Warships:\n" + "\n".join(violations)


def test_warships_game_imports_engine_only_via_api() -> None:
    violations: list[str] = []
    for path in _iter_python_files(REPO_ROOT / "warships" / "game"):
        for target in _collect_import_targets(path, top_level_only=False):
            if target == "engine" or target.startswith("engine."):
                if not target.startswith("engine.api"):
                    violations.append(f"{path.relative_to(REPO_ROOT)} -> {target}")
    assert not violations, "Warships game must import engine only via engine.api:\n" + "\n".join(
        violations
    )


def test_engine_api_has_no_top_level_runtime_or_rendering_imports() -> None:
    violations: list[str] = []
    for path in _iter_python_files(REPO_ROOT / "engine" / "api"):
        for target in _collect_import_targets(path, top_level_only=True):
            if target.startswith("engine.runtime") or target.startswith("engine.rendering"):
                violations.append(f"{path.relative_to(REPO_ROOT)} -> {target}")
    assert (
        not violations
    ), "engine.api top-level imports must not depend on runtime/rendering internals:\n" + "\n".join(
        violations
    )


def test_no_wildcard_barrel_imports_in_engine_or_game_code() -> None:
    violations: list[str] = []
    scan_roots = (REPO_ROOT / "engine", REPO_ROOT / "warships" / "game")
    for root in scan_roots:
        for path in _iter_python_files(root):
            for module in _collect_wildcard_imports(path):
                violations.append(f"{path.relative_to(REPO_ROOT)} -> from {module} import *")
    assert not violations, "Wildcard imports are forbidden in engine/game code:\n" + "\n".join(
        violations
    )

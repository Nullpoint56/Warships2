#!/usr/bin/env python3
"""Enforce feature/env flag registry metadata and expiry hygiene."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class FlagUse:
    name: str
    file: str
    line: int


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        if isinstance(fn.value, ast.Name):
            return f"{fn.value.id}.{fn.attr}"
        return fn.attr
    return ""


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _first_const_str(args: list[ast.expr], *, max_index: int = 1) -> str | None:
    for index, node in enumerate(args):
        if index > max_index:
            break
        value = _const_str(node)
        if value is not None:
            return value
    return None


def _extract_flag_uses(path: Path) -> list[FlagUse]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    uses: list[FlagUse] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {
            "os.getenv",
            "_flag",
            "_env_flag",
            "_int",
            "_env_int",
            "_float",
            "_env_float",
            "_text",
            "_csv",
            "_raw",
        }:
            arg0 = _first_const_str(node.args)
            if arg0 and ENV_NAME_RE.match(arg0):
                uses.append(FlagUse(name=arg0, file=path.as_posix(), line=node.lineno))
        elif name == "get":
            # os.environ.get("KEY")
            fn = node.func
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Attribute):
                if (
                    fn.value.attr == "environ"
                    and isinstance(fn.value.value, ast.Name)
                    and fn.value.value.id == "os"
                ):
                    arg0 = _const_str(node.args[0]) if node.args else None
                    if arg0 and ENV_NAME_RE.match(arg0):
                        uses.append(FlagUse(name=arg0, file=path.as_posix(), line=node.lineno))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "environ"
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
        ):
            key = _const_str(node.slice)
            if key and ENV_NAME_RE.match(key):
                uses.append(FlagUse(name=key, file=path.as_posix(), line=node.lineno))
    return uses


def _load_registry(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}


def _validate_remove_by(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed >= date.today()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check feature/env flag registry metadata.")
    parser.add_argument("--root", default="engine")
    parser.add_argument(
        "--registry",
        default="tools/quality/budgets/feature_flags_registry.json",
    )
    args = parser.parse_args()

    root = Path(args.root)
    registry_path = Path(args.registry)
    registry = _load_registry(registry_path)

    uses: list[FlagUse] = []
    for path in sorted(root.rglob("*.py")):
        uses.extend(_extract_flag_uses(path))

    used_names = sorted({u.name for u in uses})
    violations: list[str] = []
    required_fields = ("owner", "rationale", "remove_by", "status")

    for name in used_names:
        if name not in registry:
            refs = [u for u in uses if u.name == name][:3]
            ref_txt = ", ".join(f"{u.file}:{u.line}" for u in refs)
            violations.append(f"{name} missing registry metadata (refs: {ref_txt})")
            continue
        entry = registry[name]
        for field in required_fields:
            value = str(entry.get(field, "")).strip()
            if not value:
                violations.append(f"{name} missing required metadata field '{field}'")
        remove_by = str(entry.get("remove_by", "")).strip()
        if remove_by and not _validate_remove_by(remove_by):
            violations.append(
                f"{name} has invalid or expired remove_by '{remove_by}' (expected YYYY-MM-DD and not in the past)"
            )

    for name in sorted(registry.keys()):
        if name not in used_names:
            violations.append(f"{name} present in registry but unused in code")

    if violations:
        print("Feature flag registry violations:")
        for line in violations:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

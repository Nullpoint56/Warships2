"""Saved filter presets for Session Inspector."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EventFilterPreset:
    name: str
    category: str
    level: str
    query: str


DEFAULT_PRESETS = [
    EventFilterPreset(name="All Events", category="all", level="all", query=""),
    EventFilterPreset(
        name="Render Issues", category="render", level="all", query="resize viewport present"
    ),
    EventFilterPreset(name="Input Activity", category="input", level="all", query="pointer input"),
    EventFilterPreset(name="Warnings+Errors", category="all", level="warning", query=""),
]


def presets_path() -> Path:
    return Path("tools/data/config/session_inspector_presets.json")


def load_presets(path: Path | None = None) -> list[EventFilterPreset]:
    path = path or presets_path()
    if not path.exists():
        return list(DEFAULT_PRESETS)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return list(DEFAULT_PRESETS)
    if not isinstance(payload, dict):
        return list(DEFAULT_PRESETS)
    items = payload.get("presets", [])
    if not isinstance(items, list):
        return list(DEFAULT_PRESETS)
    parsed: list[EventFilterPreset] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed.append(
            EventFilterPreset(
                name=str(item.get("name", "")).strip() or "Unnamed",
                category=str(item.get("category", "all")).strip() or "all",
                level=str(item.get("level", "all")).strip() or "all",
                query=str(item.get("query", "")),
            )
        )
    return parsed or list(DEFAULT_PRESETS)


def save_presets(presets: list[EventFilterPreset], path: Path | None = None) -> Path:
    path = path or presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "tool.session_inspector_presets.v1",
        "presets": [
            {
                "name": preset.name,
                "category": preset.category,
                "level": preset.level,
                "query": preset.query,
            }
            for preset in presets
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path

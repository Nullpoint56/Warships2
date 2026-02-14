"""Persistence layer for loading/saving presets."""

from __future__ import annotations

import json
from pathlib import Path


class PresetRepository:
    """JSON file repository for ship placement presets."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def list_names(self) -> list[str]:
        """List available preset names."""
        return sorted(path.stem for path in self._root.glob("*.json"))

    def load_payload(self, name: str) -> dict[str, object]:
        """Load preset payload by name."""
        path = self._path_for_name(name)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_payload(self, name: str, payload: dict[str, object]) -> None:
        """Save preset payload by name."""
        path = self._path_for_name(name)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _path_for_name(self, name: str) -> Path:
        cleaned = _sanitize_name(name)
        return self._root / f"{cleaned}.json"


def _sanitize_name(name: str) -> str:
    cleaned = name.strip().replace(" ", "_")
    if not cleaned:
        raise ValueError("Preset name cannot be empty.")
    # noinspection SpellCheckingInspection
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(char not in allowed for char in cleaned):
        raise ValueError("Preset name has unsupported characters.")
    return cleaned

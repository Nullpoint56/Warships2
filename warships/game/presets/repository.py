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
        names: list[str] = []
        for path in self._root.glob("*.json"):
            ui_name = self._read_ui_name(path)
            names.append(ui_name or path.stem)
        return sorted(names, key=str.lower)

    def load_payload(self, name: str) -> dict[str, object]:
        """Load preset payload by name."""
        path = self._path_for_ui_name(name)
        if path is None:
            raise FileNotFoundError(f"Preset '{name}' not found.")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_payload(self, name: str, payload: dict[str, object]) -> None:
        """Save preset payload by name."""
        ui_name = _validate_ui_name(name)
        path = self._path_for_ui_name(ui_name, missing_ok=True)
        if path is None:
            path = self._allocate_path(ui_name)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def delete(self, name: str) -> None:
        """Delete preset by name if it exists."""
        path = self._path_for_ui_name(name, missing_ok=True)
        if path is not None and path.exists():
            path.unlink()

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename preset file."""
        old_ui = _validate_ui_name(old_name)
        new_ui = _validate_ui_name(new_name)
        old_path = self._path_for_ui_name(old_ui, missing_ok=True)
        if old_path is None or not old_path.exists():
            raise FileNotFoundError(f"Preset '{old_name}' not found.")
        existing_new = self._path_for_ui_name(new_ui, missing_ok=True)
        if existing_new is not None and existing_new != old_path:
            raise ValueError(f"Preset '{new_name}' already exists.")
        with old_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload["name"] = new_ui
        with old_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _path_for_ui_name(self, name: str, missing_ok: bool = False) -> Path | None:
        ui_name = _validate_ui_name(name)
        # Fast path for legacy files named from normalized UI text.
        legacy = self._root / f"{_normalize_for_filename(ui_name)}.json"
        if legacy.exists():
            return legacy
        for path in self._root.glob("*.json"):
            if self._read_ui_name(path) == ui_name:
                return path
        if missing_ok:
            return None
        raise FileNotFoundError(f"Preset '{ui_name}' not found.")

    def _allocate_path(self, ui_name: str) -> Path:
        base = _normalize_for_filename(ui_name)
        candidate = self._root / f"{base}.json"
        if not candidate.exists():
            return candidate
        index = 2
        while True:
            candidate = self._root / f"{base}_{index}.json"
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def _read_ui_name(path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        value = payload.get("name")
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return None


def _validate_ui_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Preset name cannot be empty.")
    return cleaned


def _normalize_for_filename(name: str) -> str:
    chars: list[str] = []
    for char in name:
        if char.isalnum() or char in {"-", "_"}:
            chars.append(char)
        elif char.isspace():
            chars.append("_")
        else:
            chars.append("_")
    normalized = "".join(chars).strip("_")
    return normalized or "preset"

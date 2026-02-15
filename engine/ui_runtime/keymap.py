"""Backend-agnostic key normalization helpers."""

from __future__ import annotations


def map_key_name(key_name: str) -> str | None:
    """Normalize backend key names to app/controller key identifiers."""
    normalized = key_name.strip().lower()
    key_map = {
        "backspace": "backspace",
        "enter": "enter",
        "return": "enter",
        "escape": "escape",
        "esc": "escape",
        "r": "r",
        "d": "d",
    }
    if normalized in key_map:
        return key_map[normalized]
    if len(normalized) == 1 and normalized.isalpha():
        return normalized
    return None


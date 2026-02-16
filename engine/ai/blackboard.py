"""Blackboard implementation."""

from __future__ import annotations

from copy import deepcopy


class RuntimeBlackboard:
    """Default blackboard based on a dict store."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        normalized = key.strip()
        if not normalized:
            raise ValueError("key must not be empty")
        self._values[normalized] = value

    def get(self, key: str) -> object | None:
        return self._values.get(key)

    def require(self, key: str) -> object:
        value = self.get(key)
        if value is None:
            raise KeyError(f"missing blackboard key: {key}")
        return value

    def has(self, key: str) -> bool:
        return key in self._values

    def remove(self, key: str) -> object | None:
        return self._values.pop(key, None)

    def snapshot(self) -> dict[str, object]:
        return deepcopy(self._values)

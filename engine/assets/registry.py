"""Typed asset registry primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, cast

from engine.api.assets import AssetHandle, AssetLoader, AssetUnloader, AssetValue

TAsset = TypeVar("TAsset")


@dataclass(slots=True)
class _LoadedAsset:
    value: AssetValue
    refs: int
    unloader: AssetUnloader | None


class RuntimeAssetRegistry:
    """Registry that loads, caches, and releases assets by kind and id."""

    def __init__(self) -> None:
        self._loaders: dict[str, tuple[AssetLoader, AssetUnloader | None]] = {}
        self._loaded: dict[tuple[str, str], _LoadedAsset] = {}

    def register_kind(
        self,
        kind: str,
        loader: AssetLoader,
        *,
        unloader: AssetUnloader | None = None,
    ) -> None:
        """Register loader (and optional unloader) for one asset kind."""
        normalized = kind.strip()
        if not normalized:
            raise ValueError("kind must not be empty")
        self._loaders[normalized] = (loader, unloader)

    def load(self, kind: str, asset_id: str) -> AssetHandle[AssetValue]:
        """Load or acquire cached asset and return its handle."""
        key = (kind, asset_id)
        loaded = self._loaded.get(key)
        if loaded is not None:
            loaded.refs += 1
            return AssetHandle(kind=kind, asset_id=asset_id)
        loader_entry = self._loaders.get(kind)
        if loader_entry is None:
            raise KeyError(f"unknown asset kind: {kind}")
        loader, unloader = loader_entry
        value = loader(asset_id)
        self._loaded[key] = _LoadedAsset(value=value, refs=1, unloader=unloader)
        return AssetHandle(kind=kind, asset_id=asset_id)

    def get(self, handle: AssetHandle[TAsset]) -> TAsset:
        """Return loaded value for a handle."""
        key = (handle.kind, handle.asset_id)
        loaded = self._loaded.get(key)
        if loaded is None:
            raise KeyError(f"asset not loaded: kind={handle.kind} id={handle.asset_id}")
        return cast(TAsset, loaded.value)

    def release(self, handle: AssetHandle[AssetValue]) -> None:
        """Release one reference from a loaded asset handle."""
        key = (handle.kind, handle.asset_id)
        loaded = self._loaded.get(key)
        if loaded is None:
            return
        loaded.refs -= 1
        if loaded.refs > 0:
            return
        if loaded.unloader is not None:
            loaded.unloader(loaded.value)
        self._loaded.pop(key, None)

    def clear(self) -> None:
        """Release all loaded assets."""
        for key, loaded in tuple(self._loaded.items()):
            if loaded.unloader is not None:
                loaded.unloader(loaded.value)
            self._loaded.pop(key, None)


AssetRegistry = RuntimeAssetRegistry

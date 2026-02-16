"""Public asset-registry API contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

TAsset = TypeVar("TAsset")
AssetLoader = Callable[[str], object]
AssetUnloader = Callable[[object], None]


@dataclass(frozen=True, slots=True)
class AssetHandle[TAsset]:
    """Opaque handle for a loaded asset."""

    kind: str
    asset_id: str


class AssetRegistry(Protocol):
    """Public registry contract for loading and retaining assets."""

    def register_kind(
        self,
        kind: str,
        loader: AssetLoader,
        *,
        unloader: AssetUnloader | None = None,
    ) -> None:
        """Register loader for one asset kind."""

    def load(self, kind: str, asset_id: str) -> AssetHandle[object]:
        """Load or acquire asset handle."""

    def get(self, handle: AssetHandle[TAsset]) -> TAsset:
        """Resolve handle to loaded value."""

    def release(self, handle: AssetHandle[object]) -> None:
        """Release one handle reference."""

    def clear(self) -> None:
        """Release all loaded assets."""


def create_asset_registry() -> AssetRegistry:
    """Create default asset-registry implementation."""
    from engine.assets.registry import RuntimeAssetRegistry

    return RuntimeAssetRegistry()

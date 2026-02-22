"""Public asset-registry API contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

TAsset = TypeVar("TAsset")


class AssetValue(Protocol):
    """Opaque asset payload boundary contract."""


AssetLoader = Callable[[str], AssetValue]
AssetUnloader = Callable[[AssetValue], None]


@dataclass(frozen=True, slots=True)
class AssetHandle[TAsset]:
    """Opaque handle for a loaded asset."""

    kind: str
    asset_id: str


class AssetRegistry(ABC):
    """Public registry contract for loading and retaining assets."""

    @abstractmethod
    def register_kind(
        self,
        kind: str,
        loader: AssetLoader,
        *,
        unloader: AssetUnloader | None = None,
    ) -> None:
        """Register loader for one asset kind."""

    @abstractmethod
    def load(self, kind: str, asset_id: str) -> AssetHandle[AssetValue]:
        """Load or acquire asset handle."""

    @abstractmethod
    def get(self, handle: AssetHandle[TAsset]) -> TAsset:
        """Resolve handle to loaded value."""

    @abstractmethod
    def release(self, handle: AssetHandle[AssetValue]) -> None:
        """Release one handle reference."""

    @abstractmethod
    def clear(self) -> None:
        """Release all loaded assets."""


def create_asset_registry() -> AssetRegistry:
    """Create default asset-registry implementation."""
    from engine.assets.registry import RuntimeAssetRegistry

    return RuntimeAssetRegistry()

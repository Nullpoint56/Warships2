from __future__ import annotations

import pytest

from engine.assets.registry import AssetHandle, AssetRegistry


def test_asset_registry_load_get_release_lifecycle() -> None:
    registry = AssetRegistry()
    unloaded: list[object] = []
    registry.register_kind(
        "text",
        loader=lambda asset_id: f"value:{asset_id}",
        unloader=lambda value: unloaded.append(value),
    )

    handle1 = registry.load("text", "a")
    handle2 = registry.load("text", "a")
    assert registry.get(handle1) == "value:a"
    assert registry.get(handle2) == "value:a"

    registry.release(handle1)
    assert unloaded == []
    registry.release(handle2)
    assert unloaded == ["value:a"]


def test_asset_registry_raises_for_unknown_kind() -> None:
    registry = AssetRegistry()
    with pytest.raises(KeyError):
        registry.load("missing", "id")


def test_asset_registry_clear_unloads_everything() -> None:
    registry = AssetRegistry()
    unloaded: list[object] = []
    registry.register_kind(
        "blob",
        loader=lambda asset_id: {"id": asset_id},
        unloader=lambda value: unloaded.append(value),
    )
    first = registry.load("blob", "x")
    second = registry.load("blob", "y")

    registry.clear()

    assert len(unloaded) == 2
    with pytest.raises(KeyError):
        registry.get(first)
    with pytest.raises(KeyError):
        registry.get(second)


def test_asset_registry_rejects_empty_kind_registration() -> None:
    registry = AssetRegistry()
    with pytest.raises(ValueError):
        registry.register_kind("", loader=lambda _: object())


def test_asset_registry_release_unknown_handle_is_noop() -> None:
    registry = AssetRegistry()
    unknown = AssetHandle(kind="missing", asset_id="id")
    registry.release(unknown)

import pytest

from warships.game.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def test_service_save_load_and_delete(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("alpha", valid_fleet)
    loaded = service.load_preset("alpha")
    assert len(loaded.ships) == len(valid_fleet.ships)
    service.delete_preset("alpha")
    assert service.list_presets() == []


def test_service_rejects_invalid_fleet(tmp_path) -> None:
    service = PresetService(PresetRepository(tmp_path))
    invalid = FleetPlacement(
        ships=[ShipPlacement(ShipType.DESTROYER, Coord(0, 9), Orientation.HORIZONTAL)]
    )
    with pytest.raises(ValueError):
        service.save_preset("bad", invalid)


def test_service_rename(tmp_path, valid_fleet) -> None:
    service = PresetService(PresetRepository(tmp_path))
    service.save_preset("old", valid_fleet)
    service.rename_preset("old", "new")
    assert "new" in service.list_presets()


def test_service_rejects_touching_fleet(tmp_path) -> None:
    service = PresetService(PresetRepository(tmp_path))
    touching = FleetPlacement(
        ships=[
            ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.BATTLESHIP, Coord(1, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CRUISER, Coord(4, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.SUBMARINE, Coord(6, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.DESTROYER, Coord(8, 0), Orientation.HORIZONTAL),
        ]
    )
    with pytest.raises(ValueError, match="cannot touch"):
        service.save_preset("touching", touching)

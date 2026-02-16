import pytest

from warships.game.core.models import FleetPlacement
from warships.game.presets.schema import fleet_to_payload, payload_to_fleet


def test_schema_roundtrip(valid_fleet: FleetPlacement) -> None:
    payload = fleet_to_payload("alpha", valid_fleet)
    name, fleet = payload_to_fleet(payload)
    assert name == "alpha"
    assert len(fleet.ships) == len(valid_fleet.ships)


def test_schema_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError):
        payload_to_fleet({"version": 1, "name": "", "grid_size": 10, "ships": []})

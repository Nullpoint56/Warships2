import pytest

from warships.game.presets.schema import payload_to_fleet


def test_schema_rejects_wrong_version_and_grid_size() -> None:
    with pytest.raises(ValueError):
        payload_to_fleet({"version": 2, "name": "x", "grid_size": 10, "ships": []})
    with pytest.raises(ValueError):
        payload_to_fleet({"version": 1, "name": "x", "grid_size": 9, "ships": []})


def test_schema_rejects_malformed_ship_entries() -> None:
    base = {"version": 1, "name": "x", "grid_size": 10}
    with pytest.raises(ValueError):
        payload_to_fleet({**base, "ships": "bad"})
    with pytest.raises(ValueError):
        payload_to_fleet({**base, "ships": [{"type": "DESTROYER", "bow": [0], "orientation": "HORIZONTAL"}]})

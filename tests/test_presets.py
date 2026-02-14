"""Tests for preset repository/service behavior."""

import random
from pathlib import Path

from warships.core.fleet import random_fleet
from warships.presets.repository import PresetRepository
from warships.presets.service import PresetService


def test_preset_roundtrip(tmp_path: Path) -> None:
    service = PresetService(PresetRepository(tmp_path))
    fleet = random_fleet(random.Random(77))

    service.save_preset("test_preset", fleet)
    loaded = service.load_preset("test_preset")

    assert len(loaded.ships) == len(fleet.ships)
    assert {ship.ship_type for ship in loaded.ships} == {ship.ship_type for ship in fleet.ships}

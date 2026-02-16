from __future__ import annotations

import random

import pytest

from warships.game.app.controller import GameController
from warships.game.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType
from warships.game.presets.repository import PresetRepository
from warships.game.presets.service import PresetService


def make_valid_fleet() -> FleetPlacement:
    return FleetPlacement(
        ships=[
            ShipPlacement(ShipType.CARRIER, Coord(0, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.BATTLESHIP, Coord(2, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.CRUISER, Coord(4, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.SUBMARINE, Coord(6, 0), Orientation.HORIZONTAL),
            ShipPlacement(ShipType.DESTROYER, Coord(8, 0), Orientation.HORIZONTAL),
        ]
    )


@pytest.fixture
def valid_fleet() -> FleetPlacement:
    return make_valid_fleet()


@pytest.fixture
def seeded_rng() -> random.Random:
    return random.Random(1337)


@pytest.fixture
def preset_service(tmp_path) -> PresetService:
    return PresetService(PresetRepository(tmp_path))


@pytest.fixture
def controller_factory(preset_service: PresetService):
    def _make(seed: int = 1337, debug_ui: bool = False) -> GameController:
        return GameController(preset_service=preset_service, rng=random.Random(seed), debug_ui=debug_ui)

    return _make

"""Preset data schema and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from warships.game.core.models import (
    BOARD_SIZE,
    Coord,
    FleetPlacement,
    Orientation,
    ShipPlacement,
    ShipType,
)


@dataclass(slots=True)
class PresetModel:
    """Serializable preset model."""

    version: int
    name: str
    grid_size: int
    ships: list[dict[str, object]]


def fleet_to_payload(name: str, fleet: FleetPlacement) -> dict[str, object]:
    """Convert fleet placement to JSON-serializable payload."""
    return {
        "version": 1,
        "name": name,
        "grid_size": BOARD_SIZE,
        "ships": [
            {
                "type": placement.ship_type.value,
                "bow": [placement.bow.row, placement.bow.col],
                "orientation": placement.orientation.value,
            }
            for placement in fleet.ships
        ],
    }


def payload_to_fleet(payload: dict[str, object]) -> tuple[str, FleetPlacement]:
    """Convert loaded payload into fleet placement."""
    raw_version = payload.get("version", -1)
    if not isinstance(raw_version, (int, str)):
        raise ValueError("Preset version must be int-compatible.")
    version = int(raw_version)
    if version != 1:
        raise ValueError("Unsupported preset version.")
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Preset name is required.")
    raw_grid_size = payload.get("grid_size", BOARD_SIZE)
    if not isinstance(raw_grid_size, (int, str)):
        raise ValueError("Preset grid_size must be int-compatible.")
    grid_size = int(raw_grid_size)
    if grid_size != BOARD_SIZE:
        raise ValueError("Preset grid size mismatch.")

    raw_ships = payload.get("ships")
    if not isinstance(raw_ships, list):
        raise ValueError("Preset ships must be a list.")

    ships: list[ShipPlacement] = []
    for item in raw_ships:
        if not isinstance(item, dict):
            raise ValueError("Each preset ship must be an object.")
        try:
            ship_type = ShipType(str(item["type"]))
            bow = item["bow"]
            if not isinstance(bow, list) or len(bow) != 2:
                raise ValueError("Ship bow must be a 2-item list.")
            row, col = int(bow[0]), int(bow[1])
            orientation = Orientation(str(item["orientation"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Malformed ship entry in preset payload.") from exc
        ships.append(
            ShipPlacement(ship_type=ship_type, bow=Coord(row=row, col=col), orientation=orientation)
        )
    return name, FleetPlacement(ships=ships)

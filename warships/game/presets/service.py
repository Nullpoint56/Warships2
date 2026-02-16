"""Preset use cases and business logic."""

from __future__ import annotations

from warships.game.core.fleet import validate_fleet
from warships.game.core.models import FleetPlacement
from warships.game.presets.repository import PresetRepository
from warships.game.presets.schema import fleet_to_payload, payload_to_fleet


class PresetService:
    """High-level preset operations with schema and rules validation."""

    def __init__(self, repository: PresetRepository) -> None:
        self._repository = repository

    def list_presets(self) -> list[str]:
        """List available preset names."""
        return self._repository.list_names()

    def save_preset(self, name: str, fleet: FleetPlacement) -> None:
        """Validate fleet and persist preset."""
        valid, reason = validate_fleet(fleet)
        if not valid:
            raise ValueError(reason)
        self._repository.save_payload(name, fleet_to_payload(name, fleet))

    def load_preset(self, name: str) -> FleetPlacement:
        """Load and validate preset into a fleet placement."""
        _, fleet = payload_to_fleet(self._repository.load_payload(name))
        valid, reason = validate_fleet(fleet)
        if not valid:
            raise ValueError(f"Preset '{name}' is invalid: {reason}")
        return fleet

    def rename_preset(self, old_name: str, new_name: str) -> None:
        """Rename preset."""
        self._repository.rename(old_name, new_name)

    def delete_preset(self, name: str) -> None:
        """Delete preset."""
        self._repository.delete(name)

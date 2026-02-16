import pytest

from warships.game.presets.repository import PresetRepository
from warships.game.presets.schema import fleet_to_payload


def test_repository_validation_and_rename_errors(tmp_path, valid_fleet) -> None:
    repo = PresetRepository(tmp_path)
    with pytest.raises(ValueError):
        repo.save_payload("   ", fleet_to_payload("x", valid_fleet))
    repo.save_payload("alpha", fleet_to_payload("alpha", valid_fleet))
    repo.save_payload("beta", fleet_to_payload("beta", valid_fleet))
    with pytest.raises(ValueError):
        repo.rename("alpha", "beta")
    with pytest.raises(FileNotFoundError):
        repo.rename("missing", "new")


def test_repository_delete_missing_is_noop(tmp_path) -> None:
    repo = PresetRepository(tmp_path)
    repo.delete("missing")
    assert repo.list_names() == []

import pytest

from warships.game.presets.repository import PresetRepository
from warships.game.presets.schema import fleet_to_payload


def test_repository_save_list_load_delete(tmp_path, valid_fleet) -> None:
    repo = PresetRepository(tmp_path)
    repo.save_payload("My Preset", fleet_to_payload("My Preset", valid_fleet))
    assert "My Preset" in repo.list_names()
    payload = repo.load_payload("My Preset")
    assert payload["name"] == "My Preset"
    repo.delete("My Preset")
    assert "My Preset" not in repo.list_names()


def test_repository_rename_updates_name(tmp_path, valid_fleet) -> None:
    repo = PresetRepository(tmp_path)
    repo.save_payload("Old", fleet_to_payload("Old", valid_fleet))
    repo.rename("Old", "New")
    assert "New" in repo.list_names()
    assert repo.load_payload("New")["name"] == "New"


def test_repository_load_missing_raises(tmp_path) -> None:
    repo = PresetRepository(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.load_payload("missing")


def test_repository_invalid_json_name_fallback(tmp_path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{invalid", encoding="utf-8")
    repo = PresetRepository(tmp_path)
    assert "broken" in repo.list_names()

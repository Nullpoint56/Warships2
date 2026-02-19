from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.engine_session_inspector.presets import (
    EventFilterPreset,
    load_presets,
    save_presets,
)


def test_presets_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    presets = [
        EventFilterPreset(name="A", category="all", level="all", query=""),
        EventFilterPreset(name="B", category="render", level="warning", query="resize"),
    ]
    written = save_presets(presets, path)
    loaded = load_presets(path)

    assert written == path
    assert [preset.name for preset in loaded] == ["A", "B"]
    assert loaded[1].query == "resize"

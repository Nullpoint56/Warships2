from __future__ import annotations

import pytest

from engine.api.ai import create_blackboard


def test_blackboard_set_get_require_remove_snapshot() -> None:
    blackboard = create_blackboard()
    blackboard.set("target", {"x": 3})
    assert blackboard.get("target") == {"x": 3}
    assert blackboard.require("target") == {"x": 3}
    assert blackboard.has("target")
    snapshot = blackboard.snapshot()
    assert snapshot == {"target": {"x": 3}}
    removed = blackboard.remove("target")
    assert removed == {"x": 3}
    assert not blackboard.has("target")


def test_blackboard_validates_keys_and_missing_require() -> None:
    blackboard = create_blackboard()
    with pytest.raises(ValueError):
        blackboard.set(" ", 1)
    with pytest.raises(KeyError):
        blackboard.require("missing")

from __future__ import annotations

from engine.gameplay.state_store import RuntimeStateStore


def test_state_store_snapshot_and_revision() -> None:
    store = RuntimeStateStore({"hp": 10})
    initial = store.snapshot()
    assert initial.revision == 0
    assert initial.value == {"hp": 10}

    changed = store.set({"hp": 9})
    assert changed.revision == 1
    assert changed.value == {"hp": 9}
    assert store.revision() == 1


def test_state_store_update_mutator() -> None:
    store = RuntimeStateStore({"hp": 5})

    next_snapshot = store.update(lambda state: {"hp": state["hp"] - 1})

    assert next_snapshot.value == {"hp": 4}
    assert next_snapshot.revision == 1


def test_state_store_get_returns_copy() -> None:
    store = RuntimeStateStore({"items": [1, 2]})
    current = store.get()
    current["items"].append(3)

    assert store.get() == {"items": [1, 2]}


def test_state_store_peek_returns_reference() -> None:
    store = RuntimeStateStore({"items": [1, 2]})
    current = store.peek()
    current["items"].append(3)
    assert store.peek() == {"items": [1, 2, 3]}

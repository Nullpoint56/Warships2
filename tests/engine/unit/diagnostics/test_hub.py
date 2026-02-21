from __future__ import annotations

from engine.diagnostics import DiagnosticEvent, DiagnosticHub


def test_hub_emits_and_filters_by_category_and_name() -> None:
    hub = DiagnosticHub(capacity=10, enabled=True)
    hub.emit(
        DiagnosticEvent(
            ts_utc="2026-01-01T00:00:00.000+00:00",
            tick=1,
            category="frame",
            name="frame.start",
        )
    )
    hub.emit_fast(category="system", name="system.update_ms", tick=1, value=1.2)
    hub.emit_fast(category="frame", name="frame.end", tick=1)

    frame_events = hub.snapshot(category="frame")
    assert len(frame_events) == 2
    assert hub.snapshot(name="system.update_ms")[0].category == "system"


def test_hub_subscriber_receives_events_until_unsubscribed() -> None:
    hub = DiagnosticHub(capacity=10, enabled=True)
    seen: list[str] = []

    token = hub.subscribe(lambda event: seen.append(event.name))
    hub.emit_fast(category="frame", name="frame.start", tick=1)
    hub.unsubscribe(token)
    hub.emit_fast(category="frame", name="frame.end", tick=1)

    assert seen == ["frame.start"]


def test_hub_can_filter_categories_and_apply_sampling() -> None:
    hub = DiagnosticHub(
        capacity=10,
        enabled=True,
        default_sampling_n=2,
        category_sampling={"window": 1},
        category_allowlist=("frame", "window"),
    )
    hub.emit_fast(category="input", name="input.event", tick=1)
    hub.emit_fast(category="frame", name="frame.one", tick=1)
    hub.emit_fast(category="frame", name="frame.two", tick=2)
    hub.emit_fast(category="window", name="window.resize", tick=3)

    events = hub.snapshot()
    assert len(events) == 2
    assert [event.category for event in events] == ["frame", "window"]
    assert [event.name for event in events] == ["frame.two", "window.resize"]

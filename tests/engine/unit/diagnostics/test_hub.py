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

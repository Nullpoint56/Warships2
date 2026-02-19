from __future__ import annotations

from tools.engine_obs_core.contracts import EventRecord
from tools.engine_session_inspector.views.events import EventFilter, apply_event_filter


def _event(category: str, level: str, name: str, value: str) -> EventRecord:
    return EventRecord(
        ts_utc="2026-01-01T00:00:00",
        tick=1,
        category=category,
        name=name,
        level=level,
        value=value,
        metadata={},
    )


def test_apply_event_filter_by_category_level_and_query() -> None:
    events = [
        _event("render", "info", "render.present", "ok"),
        _event("render", "error", "render.unhandled_exception", "boom"),
        _event("input", "warning", "input.pointer", "late"),
    ]

    result = apply_event_filter(
        events,
        EventFilter(category="render", level="error", query="boom"),
    )

    assert len(result) == 1
    assert result[0].name == "render.unhandled_exception"


def test_apply_event_filter_all_keeps_all_events() -> None:
    events = [
        _event("frame", "info", "frame.start", ""),
        _event("frame", "info", "frame.end", ""),
    ]

    result = apply_event_filter(events, EventFilter())
    assert len(result) == 2

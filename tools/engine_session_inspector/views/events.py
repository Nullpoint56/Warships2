"""View helpers for events explorer."""

from __future__ import annotations

import json
from dataclasses import dataclass

from tools.engine_obs_core.contracts import EventRecord
from tools.engine_obs_core.query import filter_events


@dataclass(frozen=True)
class EventFilter:
    category: str = "all"
    level: str = "all"
    query: str = ""


def apply_event_filter(events: list[EventRecord], filt: EventFilter) -> list[EventRecord]:
    category = None if filt.category == "all" else filt.category
    level = None if filt.level == "all" else filt.level
    return filter_events(events, category=category, level=level, text=filt.query)


def event_to_row(event: EventRecord) -> tuple[str, str, str, str, str]:
    summary = str(event.value)
    if len(summary) > 140:
        summary = summary[:137] + "..."
    return (event.ts_utc, str(event.tick), event.category, event.name, summary)


def format_event_payload(event: EventRecord) -> str:
    payload = {
        "ts_utc": event.ts_utc,
        "tick": event.tick,
        "category": event.category,
        "name": event.name,
        "level": event.level,
        "value": event.value,
        "metadata": event.metadata,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)

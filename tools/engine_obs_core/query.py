from __future__ import annotations

from tools.engine_obs_core.contracts import EventRecord


def filter_events(
    events: list[EventRecord],
    *,
    category: str | None = None,
    name: str | None = None,
    level: str | None = None,
    text: str | None = None,
) -> list[EventRecord]:
    """Basic event filter predicates for tool pages."""
    out = events
    if category is not None:
        out = [e for e in out if e.category == category]
    if name is not None:
        out = [e for e in out if e.name == name]
    if level is not None:
        level_norm = level.lower()
        out = [e for e in out if e.level.lower() == level_norm]
    if text is not None and text.strip():
        needle = text.lower().strip()
        out = [
            e
            for e in out
            if needle in e.name.lower()
            or needle in e.category.lower()
            or needle in str(e.value).lower()
            or needle in str(e.metadata).lower()
        ]
    return out

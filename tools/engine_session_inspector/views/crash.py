"""View helpers for crash diagnostics."""

from __future__ import annotations

import json

from tools.engine_obs_core.contracts import CrashBundleRecord, EventRecord


def build_crash_focus_text(
    crash: CrashBundleRecord | None,
    events: list[EventRecord],
) -> str:
    if crash is not None:
        lines = [
            f"schema_version={crash.schema_version}",
            f"captured_at_utc={crash.captured_at_utc}",
            f"tick={crash.tick}",
            f"reason={crash.reason or 'n/a'}",
            f"recent_events={len(crash.recent_events)}",
        ]
        if crash.exception is not None:
            lines.append(f"exception={json.dumps(crash.exception, ensure_ascii=True)}")
        if crash.runtime:
            lines.append(f"runtime={json.dumps(crash.runtime, ensure_ascii=True)}")
        return "\n".join(lines)

    warning_or_error = [
        event for event in events if event.level.lower() in {"warn", "warning", "error", "critical"}
    ]
    if not warning_or_error:
        return "No crash bundle loaded and no warning/error events found."

    recent = warning_or_error[-20:]
    lines = [
        "No crash bundle loaded.",
        f"warning_or_error_events={len(warning_or_error)}",
        "recent:",
    ]
    for event in recent:
        lines.append(
            f"- ts={event.ts_utc} tick={event.tick} level={event.level} category={event.category} name={event.name}"
        )
    return "\n".join(lines)

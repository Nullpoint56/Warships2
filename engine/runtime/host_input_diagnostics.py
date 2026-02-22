"""Input diagnostics helpers for EngineHost."""

from __future__ import annotations

from engine.api.input_snapshot import InputSnapshot
from engine.diagnostics.hub import DiagnosticHub


def emit_input_snapshot_diagnostics(
    *,
    diagnostics_hub: DiagnosticHub,
    frame_index: int,
    snapshot: InputSnapshot,
    connected_controller_ids: set[str],
) -> set[str]:
    diagnostics_hub.emit_fast(
        category="input",
        name="input.event_frequency",
        tick=frame_index,
        value={
            "pointer_events": int(len(snapshot.pointer_events)),
            "key_events": int(len(snapshot.key_events)),
            "wheel_events": int(len(snapshot.wheel_events)),
            "controllers": int(len(snapshot.controllers)),
        },
    )
    for name, value in snapshot.actions.values:
        if name == "meta.mapping_conflicts" and float(value) > 0:
            diagnostics_hub.emit_fast(
                category="input",
                name="input.mapping_conflict",
                tick=frame_index,
                value=float(value),
            )

    current_connected: set[str] = {
        str(controller.device_id)
        for controller in snapshot.controllers
        if bool(getattr(controller, "connected", False))
    }
    for device_id in sorted(current_connected - connected_controller_ids):
        diagnostics_hub.emit_fast(
            category="input",
            name="input.device_connected",
            tick=frame_index,
            value={"device_id": device_id},
        )
    for device_id in sorted(connected_controller_ids - current_connected):
        diagnostics_hub.emit_fast(
            category="input",
            name="input.device_disconnected",
            tick=frame_index,
            value={"device_id": device_id},
        )
    return current_connected


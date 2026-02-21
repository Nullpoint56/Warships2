"""Crash bundle capture for diagnostics."""

from __future__ import annotations

import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.diagnostics.hub import DiagnosticHub
from engine.diagnostics.json_codec import dumps_text
from engine.diagnostics.schema import ENGINE_CRASH_BUNDLE_SCHEMA_VERSION


class CrashBundleWriter:
    """Write structured crash bundles with recent diagnostics context."""

    def __init__(
        self,
        *,
        enabled: bool,
        output_dir: Path,
        recent_events_limit: int = 400,
    ) -> None:
        self._enabled = bool(enabled)
        self._output_dir = output_dir
        self._recent_events_limit = max(10, int(recent_events_limit))

    def capture_exception(
        self,
        exc: BaseException,
        *,
        tick: int,
        diagnostics_hub: DiagnosticHub | None,
        runtime_metadata: dict[str, Any] | None = None,
        profiling_snapshot: dict[str, Any] | None = None,
        replay_metadata: dict[str, Any] | None = None,
    ) -> Path | None:
        if not self._enabled:
            return None

        now = datetime.now(tz=UTC)
        stamp = now.strftime("%Y%m%dT%H%M%S")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"engine_crash_bundle_{stamp}.json"
        payload = {
            "schema_version": ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
            "captured_at_utc": now.isoformat(timespec="milliseconds"),
            "tick": int(tick),
            "exception": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__),
            },
            "runtime": {
                "python_version": sys.version,
                **(runtime_metadata or {}),
            },
            "recent_events": _serialize_events(
                diagnostics_hub.snapshot(limit=self._recent_events_limit) if diagnostics_hub else []
            ),
            "profiling": profiling_snapshot or {},
            "replay": replay_metadata or {},
        }
        return self._write_payload(payload, path=path)

    def capture_snapshot(
        self,
        *,
        tick: int,
        diagnostics_hub: DiagnosticHub | None,
        reason: str = "manual_export",
        runtime_metadata: dict[str, Any] | None = None,
        profiling_snapshot: dict[str, Any] | None = None,
        replay_metadata: dict[str, Any] | None = None,
        path: Path | None = None,
    ) -> Path | None:
        """Write a diagnostics snapshot bundle without requiring an exception."""
        if not self._enabled:
            return None

        now = datetime.now(tz=UTC)
        if path is None:
            stamp = now.strftime("%Y%m%dT%H%M%S")
            self._output_dir.mkdir(parents=True, exist_ok=True)
            path = self._output_dir / f"engine_crash_bundle_{stamp}.json"
        payload = {
            "schema_version": ENGINE_CRASH_BUNDLE_SCHEMA_VERSION,
            "captured_at_utc": now.isoformat(timespec="milliseconds"),
            "tick": int(tick),
            "reason": str(reason),
            "exception": None,
            "runtime": {
                "python_version": sys.version,
                **(runtime_metadata or {}),
            },
            "recent_events": _serialize_events(
                diagnostics_hub.snapshot(limit=self._recent_events_limit) if diagnostics_hub else []
            ),
            "profiling": profiling_snapshot or {},
            "replay": replay_metadata or {},
        }
        return self._write_payload(payload, path=path)

    @staticmethod
    def _write_payload(payload: dict[str, Any], *, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps_text(payload, pretty=True), encoding="utf-8")
        return path


def _serialize_events(events: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for event in events:
        out.append(
            {
                "ts_utc": str(getattr(event, "ts_utc", "")),
                "tick": int(getattr(event, "tick", 0)),
                "category": str(getattr(event, "category", "")),
                "name": str(getattr(event, "name", "")),
                "level": str(getattr(event, "level", "info")),
                "value": getattr(event, "value", None),
                "metadata": dict(getattr(event, "metadata", {}) or {}),
            }
        )
    return out

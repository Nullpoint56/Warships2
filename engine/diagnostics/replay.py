"""Replay capture primitives for deterministic debugging foundations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.diagnostics.hub import DiagnosticHub
from engine.diagnostics.json_codec import dumps_text
from engine.diagnostics.schema import (
    DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
    DIAG_REPLAY_SESSION_SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class ReplayCommand:
    tick: int
    command_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReplayManifest:
    schema_version: str
    replay_version: int
    seed: int | None
    build: dict[str, Any]
    command_count: int
    first_tick: int
    last_tick: int


@dataclass(frozen=True, slots=True)
class ReplayValidationMismatch:
    tick: int
    expected_hash: str
    actual_hash: str


@dataclass(frozen=True, slots=True)
class ReplayValidationResult:
    passed: bool
    total_ticks: int
    commands_applied: int
    checkpoint_count: int
    mismatches: list[ReplayValidationMismatch]


class ReplayRecorder:
    """Capture tick-indexed command stream and deterministic metadata."""

    def __init__(
        self,
        *,
        enabled: bool,
        seed: int | None,
        build: dict[str, Any] | None = None,
        hash_interval: int = 60,
        hub: DiagnosticHub | None = None,
    ) -> None:
        self._enabled = bool(enabled)
        self._seed = seed
        self._build = dict(build or {})
        self._hash_interval = max(1, int(hash_interval))
        self._hub = hub
        self._commands: list[ReplayCommand] = []
        self._frame_ticks: list[int] = []
        self._state_hashes: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def record_command(self, *, tick: int, command_type: str, payload: dict[str, Any]) -> None:
        if not self._enabled:
            return
        cmd = ReplayCommand(tick=int(tick), command_type=command_type, payload=dict(payload))
        self._commands.append(cmd)
        if self._hub is not None:
            self._hub.emit_fast(
                category="replay",
                name="replay.command",
                tick=cmd.tick,
                value=cmd.command_type,
                metadata={"payload": dict(cmd.payload)},
            )

    def mark_frame(self, *, tick: int, state_hash: str | None = None) -> None:
        if not self._enabled:
            return
        tick_i = int(tick)
        self._frame_ticks.append(tick_i)
        if state_hash is not None and tick_i % self._hash_interval == 0:
            hash_value = compute_state_hash(state_hash)
            hash_entry = {"tick": tick_i, "hash": hash_value}
            self._state_hashes.append(hash_entry)
            if self._hub is not None:
                self._hub.emit_fast(
                    category="replay",
                    name="replay.state_hash",
                    tick=tick_i,
                    value=hash_value,
                )

    def manifest(self) -> ReplayManifest:
        if self._frame_ticks:
            first_tick = min(self._frame_ticks)
            last_tick = max(self._frame_ticks)
        else:
            first_tick = 0
            last_tick = 0
        return ReplayManifest(
            schema_version=DIAG_REPLAY_MANIFEST_SCHEMA_VERSION,
            replay_version=1,
            seed=self._seed,
            build=dict(self._build),
            command_count=len(self._commands),
            first_tick=first_tick,
            last_tick=last_tick,
        )

    def snapshot(self, *, limit: int = 5_000) -> dict[str, Any]:
        commands = self._commands[-max(1, int(limit)) :]
        manifest = self.manifest()
        return {
            "schema_version": DIAG_REPLAY_SESSION_SCHEMA_VERSION,
            "manifest": {
                "schema_version": manifest.schema_version,
                "replay_version": manifest.replay_version,
                "seed": manifest.seed,
                "build": manifest.build,
                "command_count": manifest.command_count,
                "first_tick": manifest.first_tick,
                "last_tick": manifest.last_tick,
            },
            "commands": [
                {"tick": c.tick, "type": c.command_type, "payload": dict(c.payload)}
                for c in commands
            ],
            "state_hashes": list(self._state_hashes),
        }

    def export_json(self, *, path: Path, limit: int = 5_000) -> Path:
        payload = self.snapshot(limit=limit)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps_text(payload, pretty=True), encoding="utf-8")
        return path


class FixedStepReplayRunner:
    """Replay command stream over fixed ticks and validate checkpoint hashes."""

    def __init__(self, *, fixed_step_seconds: float) -> None:
        if fixed_step_seconds <= 0.0:
            raise ValueError("fixed_step_seconds must be > 0")
        self._fixed_step_seconds = float(fixed_step_seconds)

    def run(
        self,
        session: dict[str, Any],
        *,
        apply_command: Any,
        step: Any,
    ) -> ReplayValidationResult:
        manifest = session.get("manifest", {})
        first_tick = int(manifest.get("first_tick", 0))
        last_tick = int(manifest.get("last_tick", first_tick))
        commands_raw = session.get("commands", [])
        checkpoints_raw = session.get("state_hashes", [])

        by_tick: dict[int, list[ReplayCommand]] = {}
        for item in commands_raw:
            if not isinstance(item, dict):
                continue
            tick = int(item.get("tick", 0))
            cmd = ReplayCommand(
                tick=tick,
                command_type=str(item.get("type", "")),
                payload=dict(item.get("payload", {}) or {}),
            )
            by_tick.setdefault(tick, []).append(cmd)

        expected: dict[int, str] = {}
        for item in checkpoints_raw:
            if not isinstance(item, dict):
                continue
            tick = int(item.get("tick", 0))
            value = str(item.get("hash", ""))
            if value:
                expected[tick] = value

        mismatches: list[ReplayValidationMismatch] = []
        commands_applied = 0
        if last_tick < first_tick:
            first_tick, last_tick = last_tick, first_tick
        for tick in range(first_tick, last_tick + 1):
            for command in by_tick.get(tick, ()):
                apply_command(command)
                commands_applied += 1
            state = step(self._fixed_step_seconds)
            if tick not in expected:
                continue
            actual_hash = compute_state_hash(state)
            expected_hash = expected[tick]
            if actual_hash != expected_hash:
                mismatches.append(
                    ReplayValidationMismatch(
                        tick=tick,
                        expected_hash=expected_hash,
                        actual_hash=actual_hash,
                    )
                )

        total_ticks = max(0, last_tick - first_tick + 1)
        return ReplayValidationResult(
            passed=not mismatches,
            total_ticks=total_ticks,
            commands_applied=commands_applied,
            checkpoint_count=len(expected),
            mismatches=mismatches,
        )


def compute_state_hash(value: Any) -> str:
    """Compute stable hash for deterministic replay checkpoints."""
    normalized = dumps_text(value, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

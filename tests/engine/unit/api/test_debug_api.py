from __future__ import annotations

from pathlib import Path

from engine.api.input_snapshot import InputSnapshot
from engine.api.debug import (
    export_crash_bundle,
    export_profiling_snapshot,
    export_replay_session,
    get_diagnostics_snapshot,
    get_metrics_snapshot,
    get_profiling_snapshot,
    get_replay_manifest,
    get_replay_snapshot,
    validate_replay_snapshot,
)
from engine.runtime.host import EngineHost


class _FakeModule:
    def on_start(self, host) -> None:
        _ = host

    def on_frame(self, context) -> None:
        _ = context

    def on_input_snapshot(self, snapshot: InputSnapshot) -> bool:
        _ = snapshot
        return False

    def simulate(self, context) -> None:
        self.on_frame(context)

    def build_render_snapshot(self):
        return None

    def should_close(self) -> bool:
        return False

    def on_shutdown(self) -> None:
        return


def test_debug_api_returns_diagnostics_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    host = EngineHost(module=_FakeModule())
    host.frame()

    payload = get_diagnostics_snapshot(host, category="frame")

    assert payload.schema_version == "diag.snapshot.v1"
    assert payload.events
    assert all(event["category"] == "frame" for event in payload.events)


def test_debug_api_returns_metrics_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    host = EngineHost(module=_FakeModule())
    host.frame()

    metrics = get_metrics_snapshot(host)

    assert metrics.schema_version == "diag.metrics.v1"
    assert metrics.frame_count >= 1
    assert metrics.rolling_frame_ms >= 0.0
    assert metrics.rolling_render_ms >= 0.0
    assert metrics.resize_count >= 0
    assert metrics.resize_event_to_apply_p95_ms >= 0.0
    assert metrics.resize_apply_to_frame_p95_ms >= 0.0


def test_debug_api_returns_profiling_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_PROFILING_MODE", "timeline")
    host = EngineHost(module=_FakeModule())
    host.frame()

    profile = get_profiling_snapshot(host, limit=100)
    assert profile.schema_version == "diag.profiling.v1"
    assert profile.mode == "timeline"
    assert profile.span_count >= 1


def test_debug_api_exports_profiling_snapshot(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENGINE_METRICS_ENABLED", "1")
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_PROFILING_MODE", "timeline")
    host = EngineHost(module=_FakeModule())
    host.frame()

    output = export_profiling_snapshot(host, path=str(tmp_path / "profiling.json"))
    assert output is not None
    assert Path(output).exists()


def test_debug_api_exports_crash_bundle(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_CRASH_ENABLED", "1")
    host = EngineHost(module=_FakeModule())
    host.frame()

    output = export_crash_bundle(host, path=str(tmp_path / "crash_bundle.json"))
    assert output is not None
    assert Path(output).exists()


def test_debug_api_replay_manifest_and_export(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", "1")
    monkeypatch.setenv("WARSHIPS_RNG_SEED", "777")
    host = EngineHost(module=_FakeModule())
    host.frame()

    manifest = get_replay_manifest(host)
    assert manifest.schema_version == "diag.replay_manifest.v1"
    assert manifest.seed == 777

    output = export_replay_session(host, path=str(tmp_path / "replay.json"))
    assert output is not None
    assert Path(output).exists()


def test_debug_api_replay_snapshot_and_validation(monkeypatch) -> None:
    monkeypatch.setenv("ENGINE_DIAGNOSTICS_REPLAY_ENABLED", "1")
    host = EngineHost(module=_FakeModule())
    host.frame()

    snapshot = get_replay_snapshot(host)
    assert snapshot.schema_version == "diag.replay_session.v1"

    state = {"count": 0}

    def apply_command(_command) -> None:
        return

    def step(_dt: float) -> dict[str, int]:
        return {"count": state["count"]}

    result = validate_replay_snapshot(
        {
            "manifest": {"first_tick": 0, "last_tick": 0},
            "commands": [],
            "state_hashes": [],
        },
        fixed_step_seconds=1.0 / 60.0,
        apply_command=apply_command,
        step=step,
    )
    assert result.schema_version == "diag.replay_validation.v1"
    assert result.passed is True


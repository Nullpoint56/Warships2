from __future__ import annotations

from tools.engine_obs_core.contracts import (
    has_schema_version,
    is_crash_bundle_payload,
    is_profiling_payload,
    is_replay_payload,
)


def test_schema_guards_accept_valid_payloads() -> None:
    assert has_schema_version({"schema_version": "diag.profiling.v1"}, "diag.profiling.v1")
    assert is_profiling_payload({"schema_version": "diag.profiling.v1"})
    assert is_replay_payload({"schema_version": "diag.replay_session.v1"})
    assert is_crash_bundle_payload({"schema_version": "engine.crash_bundle.v1"})


def test_schema_guards_reject_invalid_payloads() -> None:
    assert not is_profiling_payload({"schema_version": "diag.profiling.v2"})
    assert not is_replay_payload({"schema_version": "diag.replay_manifest.v1"})
    assert not is_crash_bundle_payload({"schema_version": "engine.crash_bundle.v2"})
    assert not is_crash_bundle_payload({})

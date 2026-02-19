from __future__ import annotations

import json
from pathlib import Path

from tools.engine_obs_core.datasource.file_source import FileObsSource


def _write_session_files(root: Path) -> None:
    run_line = (
        '{"ts":"2026-01-01T00:00:00","logger":"engine.runtime",'
        '"level":"INFO","msg":"frame_metrics frame=1 dt_ms=16.0"}\n'
    )
    (root / "warships_run_20260101T000000.jsonl").write_text(
        run_line,
        encoding="utf-8",
    )
    (root / "ui_diag_run_20260101T000000.jsonl").write_text(
        '{"ts_utc":"2026-01-01T00:00:00","frame_seq":1,"reasons":["draw"]}\n',
        encoding="utf-8",
    )


def test_file_source_loads_profile_replay_and_crash_exports(tmp_path: Path) -> None:
    _write_session_files(tmp_path)

    profiles_dir = tmp_path / "tools" / "data" / "profiles"
    replay_dir = tmp_path / "tools" / "data" / "replay"
    crash_dir = tmp_path / "tools" / "data" / "crash"
    profiles_dir.mkdir(parents=True)
    replay_dir.mkdir(parents=True)
    crash_dir.mkdir(parents=True)

    (profiles_dir / "profile_sample.json").write_text(
        json.dumps(
            {
                "schema_version": "diag.profiling.v1",
                "spans": [
                    {
                        "tick": 1,
                        "category": "host",
                        "name": "frame",
                        "start_s": 1.0,
                        "end_s": 1.01,
                        "duration_ms": 10.0,
                        "metadata": {"frame_index": 1},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    (replay_dir / "replay_sample.json").write_text(
        json.dumps(
            {
                "schema_version": "diag.replay_session.v1",
                "manifest": {"first_tick": 1, "last_tick": 1},
                "commands": [{"tick": 1, "type": "input.key", "payload": {"value": "a"}}],
                "state_hashes": [{"tick": 1, "hash": "abc"}],
            }
        ),
        encoding="utf-8",
    )

    (crash_dir / "crash_sample.json").write_text(
        json.dumps(
            {
                "schema_version": "engine.crash_bundle.v1",
                "captured_at_utc": "2026-01-01T00:00:00",
                "tick": 42,
                "reason": "manual_export",
                "exception": None,
                "runtime": {"engine": "test"},
                "recent_events": [],
                "profiling": {},
                "replay": {},
            }
        ),
        encoding="utf-8",
    )

    source = FileObsSource(tmp_path, recursive=False)
    session = source.list_sessions()[0]

    spans = source.load_spans(session, limit=100)
    assert len(spans) == 1
    assert spans[0].duration_ms == 10.0

    replay = source.load_replay(session)
    assert len(replay.commands) == 1
    assert replay.commands[0].type == "input.key"
    assert len(replay.checkpoints) == 1

    crash = source.load_crash(session)
    assert crash is not None
    assert crash.tick == 42
    assert crash.reason == "manual_export"

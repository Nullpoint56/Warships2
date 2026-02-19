from __future__ import annotations

from pathlib import Path

from tools.engine_obs_core.datasource.file_source import FileObsSource


def _write_session_files(root: Path) -> None:
    run = root / "warships_run_20260101T000000.jsonl"
    ui = root / "ui_diag_run_20260101T000000.jsonl"
    run.write_text(
        "\n".join(
            [
                '{"ts":"2026-01-01T00:00:00","logger":"engine.runtime","level":"INFO","msg":"frame_metrics frame=1 dt_ms=16.0"}',
                '{"ts":"2026-01-01T00:00:01","logger":"engine.rendering.scene","level":"INFO","msg":"resize_event"}',
            ]
        ),
        encoding="utf-8",
    )
    ui.write_text(
        "\n".join(
            [
                '{"ts_utc":"2026-01-01T00:00:00","frame_seq":1,"reasons":["draw"],"timing":{"apply_to_frame_ms":1.0}}',
                '{"ts_utc":"2026-01-01T00:00:00.016","frame_seq":2,"reasons":["draw"],"timing":{"apply_to_frame_ms":1.2}}',
                '{"ts_utc":"2026-01-01T00:00:00.032","frame_seq":3,"reasons":["draw"],"timing":{"apply_to_frame_ms":1.1}}',
            ]
        ),
        encoding="utf-8",
    )


def test_file_source_loads_sessions_events_and_metrics(tmp_path: Path) -> None:
    _write_session_files(tmp_path)
    source = FileObsSource(tmp_path, recursive=False)

    sessions = source.list_sessions()
    assert len(sessions) == 1

    events = source.load_events(sessions[0])
    assert events
    assert any(event.category == "frame" for event in events)
    assert any(event.category == "ui_diag" for event in events)

    metrics = source.load_metrics(sessions[0])
    assert metrics.frame_points
    assert metrics.frame_points[0].frame_ms >= 0.0

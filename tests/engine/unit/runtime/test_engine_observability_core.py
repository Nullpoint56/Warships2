from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api.debug import discover_debug_sessions, load_debug_session  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "\n".join(json.dumps(r) for r in rows)
    path.write_text(text, encoding="utf-8")


def test_discover_session_bundles_pairs_nearest_run(tmp_path: Path) -> None:
    run1 = tmp_path / "warships_run_20260218T200000.jsonl"
    run2 = tmp_path / "warships_run_20260218T200100.jsonl"
    ui1 = tmp_path / "ui_diag_run_20260218T200001_01.jsonl"
    ui2 = tmp_path / "ui_diag_run_20260218T200101_01.jsonl"
    for p in (run1, run2, ui1, ui2):
        p.write_text("", encoding="utf-8")

    bundles = discover_debug_sessions(tmp_path)

    assert len(bundles) == 2
    assert bundles[0].run_log == run1
    assert bundles[0].ui_log == ui1
    assert bundles[1].run_log == run2
    assert bundles[1].ui_log == ui2


def test_load_session_summary_metrics_and_hitches(tmp_path: Path) -> None:
    run_log = tmp_path / "warships_run_20260218T200000.jsonl"
    ui_log = tmp_path / "ui_diag_run_20260218T200000_01.jsonl"

    _write_jsonl(
        run_log,
        [
            {"ts": "2026-02-18T20:00:00.000+00:00", "level": "INFO", "msg": "start"},
            {"ts": "2026-02-18T20:00:00.050+00:00", "level": "WARNING", "msg": "warn sample"},
            {"ts": "2026-02-18T20:00:00.100+00:00", "level": "ERROR", "msg": "error sample"},
        ],
    )
    _write_jsonl(
        ui_log,
        [
            {
                "frame_seq": 1,
                "ts_utc": "2026-02-18T20:00:00.000+00:00",
                "timing": {"event_to_frame_ms": 1.0, "apply_to_frame_ms": 0.8},
            },
            {
                "frame_seq": 2,
                "ts_utc": "2026-02-18T20:00:00.008+00:00",
                "timing": {"event_to_frame_ms": 2.0, "apply_to_frame_ms": 1.2},
            },
            {
                "frame_seq": 3,
                "ts_utc": "2026-02-18T20:00:00.041+00:00",
                "timing": {"event_to_frame_ms": 3.0, "apply_to_frame_ms": 2.2},
            },
        ],
    )

    bundles = discover_debug_sessions(tmp_path)
    assert len(bundles) == 1

    loaded = load_debug_session(bundles[0])
    summary = loaded.summary

    assert summary.frame_count == 3
    assert summary.hitch_count_25ms == 1
    assert summary.hitches_25ms[0].frame_seq == 3
    assert summary.warning_count == 1
    assert summary.error_count == 1
    assert summary.fps_mean is not None
    assert summary.frame_time_max_ms is not None
    assert summary.frame_time_max_ms >= 33.0


def test_discover_session_bundles_recursive_finds_nested_logs(tmp_path: Path) -> None:
    nested = tmp_path / "warships" / "appdata" / "logs"
    nested.mkdir(parents=True, exist_ok=True)
    run_log = nested / "warships_run_20260218T210000.jsonl"
    ui_log = nested / "ui_diag_run_20260218T210000_01.jsonl"
    run_log.write_text("", encoding="utf-8")
    ui_log.write_text("", encoding="utf-8")

    direct = discover_debug_sessions(tmp_path)
    recursive = discover_debug_sessions(tmp_path, recursive=True)

    assert direct == []
    assert len(recursive) == 1
    assert recursive[0].run_log == run_log
    assert recursive[0].ui_log == ui_log

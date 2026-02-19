from __future__ import annotations

import argparse
import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SessionBundle:
    run_log: Path | None
    ui_log: Path | None
    run_stamp: datetime | None
    ui_stamp: datetime | None


@dataclass(frozen=True)
class HitchRecord:
    frame_seq: int
    frame_time_ms: float
    ts_utc: datetime | None


@dataclass(frozen=True)
class SessionSummary:
    frame_count: int
    fps_mean: float | None
    frame_time_p50_ms: float | None
    frame_time_p95_ms: float | None
    frame_time_p99_ms: float | None
    frame_time_max_ms: float | None
    hitch_count_25ms: int
    hitches_25ms: list[HitchRecord]
    event_to_frame_p95_ms: float | None
    apply_to_frame_p95_ms: float | None
    warning_count: int
    error_count: int


@dataclass(frozen=True)
class LoadedSession:
    bundle: SessionBundle
    run_records: list[dict[str, Any]]
    ui_frames: list[dict[str, Any]]
    summary: SessionSummary


def _safe_json_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _parse_iso_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_stamp(path: Path, prefix: str) -> datetime | None:
    name = path.stem
    # New pattern: <game>_<kind>_<YYYYMMDDTHHMMSS>[...]
    match = re.search(r"_(\d{8}T\d{6})(?:_|$)", name)
    if match:
        raw = match.group(1)
    else:
        # Legacy pattern support: warships_run_<stamp>, ui_diag_run_<stamp>
        if not path.name.startswith(prefix):
            return None
        raw = path.name[len(prefix) :]
        if raw.endswith(".jsonl"):
            raw = raw[:-6]
        raw = raw.split("_", 1)[0]
    try:
        return datetime.strptime(raw, "%Y%m%dT%H%M%S")
    except ValueError:
        return None


def _percentile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    i = q * (len(sorted_values) - 1)
    lo = int(i)
    hi = min(lo + 1, len(sorted_values) - 1)
    w = i - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    return _percentile(sorted_values, 0.95)


def discover_session_bundles(log_dir: Path, *, recursive: bool = False) -> list[SessionBundle]:
    search_roots = [log_dir]
    if log_dir.name == "logs":
        # Allow passing appdata/logs while ui traces are in sibling appdata/ui.
        search_roots.append(log_dir.parent)
    if recursive:
        run_logs = []
        ui_logs = []
        for root in search_roots:
            run_logs.extend(root.rglob("*_logs_*.jsonl"))
            run_logs.extend(root.rglob("warships_run_*.jsonl"))
            ui_logs.extend(root.rglob("*_ui_trace_*.jsonl"))
            ui_logs.extend(root.rglob("ui_diag_run_*.jsonl"))
        run_logs = sorted(set(run_logs))
        ui_logs = sorted(set(ui_logs))
    else:
        run_logs = []
        ui_logs = []
        for root in search_roots:
            run_logs.extend(root.glob("*_logs_*.jsonl"))
            run_logs.extend(root.glob("warships_run_*.jsonl"))
            ui_logs.extend(root.glob("*_ui_trace_*.jsonl"))
            ui_logs.extend(root.glob("ui_diag_run_*.jsonl"))
        run_logs = sorted(set(run_logs))
        ui_logs = sorted(set(ui_logs))
    run_items = [(p, _extract_stamp(p, "warships_run_")) for p in run_logs]
    ui_items = [(p, _extract_stamp(p, "ui_diag_run_")) for p in ui_logs]

    bundles: list[SessionBundle] = []
    used_runs: set[Path] = set()
    for ui_path, ui_stamp in ui_items:
        best_run: Path | None = None
        best_stamp: datetime | None = None
        best_delta: float | None = None
        if ui_stamp is not None:
            for run_path, run_stamp in run_items:
                if run_stamp is None:
                    continue
                delta = abs((ui_stamp - run_stamp).total_seconds())
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_run = run_path
                    best_stamp = run_stamp
        bundles.append(
            SessionBundle(
                run_log=best_run,
                ui_log=ui_path,
                run_stamp=best_stamp,
                ui_stamp=ui_stamp,
            )
        )
        if best_run is not None:
            used_runs.add(best_run)

    for run_path, run_stamp in run_items:
        if run_path in used_runs:
            continue
        bundles.append(
            SessionBundle(run_log=run_path, ui_log=None, run_stamp=run_stamp, ui_stamp=None)
        )

    bundles.sort(
        key=lambda b: (
            b.ui_stamp or b.run_stamp or datetime.min,
            str(b.ui_log or b.run_log or ""),
        )
    )
    return bundles


def _load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = _safe_json_line(line)
        if row is not None:
            out.append(row)
    return out


def _frame_time_ms(frames: list[dict[str, Any]]) -> tuple[list[float], list[HitchRecord]]:
    frame_ts: list[tuple[int, datetime]] = []
    for f in frames:
        seq = f.get("frame_seq")
        ts = _parse_iso_timestamp(f.get("ts_utc"))
        if isinstance(seq, int) and ts is not None:
            frame_ts.append((seq, ts))
    frame_ts.sort(key=lambda x: x[0])
    dts: list[float] = []
    hitches: list[HitchRecord] = []
    for i in range(1, len(frame_ts)):
        seq, ts = frame_ts[i]
        prev_ts = frame_ts[i - 1][1]
        dt = (ts - prev_ts).total_seconds() * 1000.0
        if dt <= 0:
            continue
        dts.append(dt)
        if dt >= 25.0:
            hitches.append(HitchRecord(frame_seq=seq, frame_time_ms=dt, ts_utc=ts))
    return dts, hitches


def _timing_value(frame: dict[str, Any], key: str) -> float | None:
    timing = frame.get("timing")
    if not isinstance(timing, dict):
        return None
    value = timing.get(key)
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def summarize_session(
    run_records: list[dict[str, Any]], ui_frames: list[dict[str, Any]]
) -> SessionSummary:
    frame_dts, hitches = _frame_time_ms(ui_frames)
    frame_dts_sorted = sorted(frame_dts)
    fps_mean = None
    if frame_dts:
        mean_ms = statistics.fmean(frame_dts)
        if mean_ms > 0.0:
            fps_mean = 1000.0 / mean_ms

    event_to_frame: list[float] = []
    apply_to_frame: list[float] = []
    for frame in ui_frames:
        e = _timing_value(frame, "event_to_frame_ms")
        a = _timing_value(frame, "apply_to_frame_ms")
        if e is not None:
            event_to_frame.append(e)
        if a is not None:
            apply_to_frame.append(a)

    warning_count = 0
    error_count = 0
    for rec in run_records:
        level = str(rec.get("level", "")).upper()
        msg = str(rec.get("msg", ""))
        if level in {"WARNING", "WARN"} or " warning " in f" {msg.lower()} ":
            warning_count += 1
        if level in {"ERROR", "CRITICAL"} or " exception" in msg.lower():
            error_count += 1

    return SessionSummary(
        frame_count=len(ui_frames),
        fps_mean=fps_mean,
        frame_time_p50_ms=_percentile(frame_dts_sorted, 0.50),
        frame_time_p95_ms=_percentile(frame_dts_sorted, 0.95),
        frame_time_p99_ms=_percentile(frame_dts_sorted, 0.99),
        frame_time_max_ms=max(frame_dts) if frame_dts else None,
        hitch_count_25ms=len(hitches),
        hitches_25ms=hitches,
        event_to_frame_p95_ms=_p95(event_to_frame),
        apply_to_frame_p95_ms=_p95(apply_to_frame),
        warning_count=warning_count,
        error_count=error_count,
    )


def load_session(bundle: SessionBundle) -> LoadedSession:
    run_records = _load_jsonl(bundle.run_log)
    ui_records = _load_jsonl(bundle.ui_log)
    ui_frames = [r for r in ui_records if isinstance(r.get("frame_seq"), int)]
    ui_frames.sort(key=lambda r: int(r["frame_seq"]))
    summary = summarize_session(run_records=run_records, ui_frames=ui_frames)
    return LoadedSession(
        bundle=bundle, run_records=run_records, ui_frames=ui_frames, summary=summary
    )


def _format_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _print_session_summary(session: LoadedSession) -> None:
    run_name = session.bundle.run_log.name if session.bundle.run_log else "n/a"
    ui_name = session.bundle.ui_log.name if session.bundle.ui_log else "n/a"
    s = session.summary
    print(f"run_log={run_name}")
    print(f"ui_log={ui_name}")
    print(f"frame_count={s.frame_count}")
    print(f"fps_mean={_format_float(s.fps_mean)}")
    print(f"frame_time_p50_ms={_format_float(s.frame_time_p50_ms)}")
    print(f"frame_time_p95_ms={_format_float(s.frame_time_p95_ms)}")
    print(f"frame_time_p99_ms={_format_float(s.frame_time_p99_ms)}")
    print(f"frame_time_max_ms={_format_float(s.frame_time_max_ms)}")
    print(f"hitch_count_25ms={s.hitch_count_25ms}")
    print(f"event_to_frame_p95_ms={_format_float(s.event_to_frame_p95_ms)}")
    print(f"apply_to_frame_p95_ms={_format_float(s.apply_to_frame_p95_ms)}")
    print(f"warning_count={s.warning_count}")
    print(f"error_count={s.error_count}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase-1 engine observability CLI: discover sessions and print summary metrics."
    )
    parser.add_argument(
        "--logs-dir", type=Path, default=Path.cwd(), help="Directory containing *.jsonl logs"
    )
    parser.add_argument(
        "--run-log", type=Path, default=None, help="Explicit warships_run_*.jsonl path"
    )
    parser.add_argument(
        "--ui-log", type=Path, default=None, help="Explicit ui_diag_run_*.jsonl path"
    )
    parser.add_argument("--list", action="store_true", help="List discovered session bundles")
    parser.add_argument("--session-index", type=int, default=0, help="Session index to summarize")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Discover session logs recursively under --logs-dir.",
    )
    args = parser.parse_args(argv)

    if args.run_log is not None or args.ui_log is not None:
        bundle = SessionBundle(
            run_log=args.run_log, ui_log=args.ui_log, run_stamp=None, ui_stamp=None
        )
        _print_session_summary(load_session(bundle))
        return 0

    bundles = discover_session_bundles(args.logs_dir, recursive=args.recursive)
    if args.list:
        if not bundles:
            print("No sessions discovered.")
            return 0
        for i, b in enumerate(bundles):
            run_name = b.run_log.name if b.run_log else "n/a"
            ui_name = b.ui_log.name if b.ui_log else "n/a"
            print(f"[{i}] run={run_name} ui={ui_name}")
        return 0
    if not bundles:
        print("No sessions discovered.")
        return 0
    index = max(0, min(args.session_index, len(bundles) - 1))
    _print_session_summary(load_session(bundles[index]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

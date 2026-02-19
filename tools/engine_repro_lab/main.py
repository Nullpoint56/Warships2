from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tools.engine_repro_lab.app import render_result_table
from tools.engine_repro_lab.batch import run_batch_validation, summarize_batch_runs
from tools.engine_repro_lab.diff import compare_batch_runs
from tools.engine_repro_lab.reporting import build_report, export_report
from tools.engine_repro_lab.runner import ValidationConfig, run_validation_from_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="engine_repro_lab")
    parser.add_argument("--version", action="store_true", help="Print tool version")
    parser.add_argument("--replay-json", type=Path, default=None, help="Replay session JSON file.")
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="Validate all replay JSON files in directory.",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=None,
        help="Baseline replay directory for differential comparison.",
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=None,
        help="Candidate replay directory for differential comparison.",
    )
    parser.add_argument(
        "--fixed-step-seconds",
        type=float,
        default=1.0 / 60.0,
        help="Fixed simulation step seconds.",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Optional output path for validation report JSON.",
    )
    return parser


def _default_simulator() -> tuple[Any, Any]:
    state = {"tick": -1, "command_count": 0}

    def apply_command(_command: Any) -> None:
        state["command_count"] += 1

    def step(_dt: float) -> dict[str, int]:
        state["tick"] += 1
        # Deterministic shape for MVP runner.
        return {"tick": state["tick"], "command_count": state["command_count"]}

    return apply_command, step


def main() -> int:
    args = build_parser().parse_args()
    if args.version:
        print("engine_repro_lab v0.1")
        return 0

    config = ValidationConfig(fixed_step_seconds=float(args.fixed_step_seconds))

    if args.batch_dir is not None:
        replay_paths = sorted(args.batch_dir.glob("*.json"))
        if not replay_paths:
            fallback_dirs = [
                Path("warships/appdata/replay"),
                Path("warships/appdata/logs/replay"),
            ]
            for directory in fallback_dirs:
                candidate_paths = sorted(directory.glob("*.json"))
                if candidate_paths:
                    replay_paths = candidate_paths
                    print(
                        f"No replay JSON files found in: {args.batch_dir}; "
                        f"using fallback directory: {directory}"
                    )
                    break
        if not replay_paths:
            print(f"No replay JSON files found in: {args.batch_dir}")
            print(
                "Hint: export replay capture first, then rerun with --batch-dir <replay_dir> "
                "(common dirs: tools/data/replay, warships/appdata/replay)."
            )
            return 0
        runs = run_batch_validation(
            replay_paths,
            config=config,
            simulator_factory=_default_simulator,
        )
        summary = summarize_batch_runs(runs)
        print(f"total_replays={summary.total_replays}")
        print(f"passed={summary.passed_count} failed={summary.failed_count}")
        print(f"total_mismatches={summary.total_mismatches}")
        worst_line = (
            f"worst_replay={summary.worst_replay} "
            f"worst_mismatch_count={summary.worst_mismatch_count}"
        )
        print(worst_line)
        return 0 if summary.failed_count == 0 else 1

    if args.baseline_dir is not None or args.candidate_dir is not None:
        if args.baseline_dir is None or args.candidate_dir is None:
            print("Both --baseline-dir and --candidate-dir are required for differential mode.")
            return 2
        baseline_paths = sorted(args.baseline_dir.glob("*.json"))
        candidate_paths = sorted(args.candidate_dir.glob("*.json"))
        baseline_runs = run_batch_validation(
            baseline_paths,
            config=config,
            simulator_factory=_default_simulator,
        )
        candidate_runs = run_batch_validation(
            candidate_paths,
            config=config,
            simulator_factory=_default_simulator,
        )
        diffs, summary = compare_batch_runs(baseline_runs, candidate_runs)
        print(f"total_compared={summary.total_compared}")
        summary_line = (
            f"regressions={summary.regressions} "
            f"improvements={summary.improvements} "
            f"unchanged={summary.unchanged}"
        )
        print(summary_line)
        print(f"missing_in_candidate={len(summary.missing_in_candidate)}")
        print(f"missing_in_baseline={len(summary.missing_in_baseline)}")
        if diffs:
            first = diffs[0]
            divergence_tick = (
                first.first_divergence.tick if first.first_divergence is not None else "n/a"
            )
            print(
                f"sample_diff replay={first.replay_path} "
                f"delta={first.mismatch_delta} "
                f"first_divergence_tick={divergence_tick}"
            )
        return 0 if summary.regressions == 0 else 1

    replay_path = args.replay_json
    if replay_path is None:
        default_batch_dir = Path("tools/data/replay")
        replay_paths = sorted(default_batch_dir.glob("*.json"))
        if replay_paths:
            runs = run_batch_validation(
                replay_paths,
                config=config,
                simulator_factory=_default_simulator,
            )
            summary = summarize_batch_runs(runs)
            print(f"total_replays={summary.total_replays}")
            print(f"passed={summary.passed_count} failed={summary.failed_count}")
            print(f"total_mismatches={summary.total_mismatches}")
            return 0 if summary.failed_count == 0 else 1
        print("Missing --replay-json and no default replay batch found.")
        print(
            "Use --replay-json <file> or --batch-dir <dir>. Default checked path: tools/data/replay"
        )
        return 0
    if not replay_path.exists():
        print(f"Replay file not found: {replay_path}")
        return 2

    apply_command, step = _default_simulator()
    run = run_validation_from_file(
        replay_path,
        config=config,
        apply_command=apply_command,
        step=step,
    )

    print(render_result_table(run))

    report_out = args.report_out
    if report_out is not None:
        report = build_report(run)
        out_path = export_report(report, report_out)
        print(f"report_written={out_path}")

    return 0 if run.result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

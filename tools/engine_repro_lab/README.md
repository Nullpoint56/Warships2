# engine_repro_lab

Deterministic replay validation tool.

Current capabilities:
- Single replay validation (`--replay-json`).
- Batch replay validation (`--batch-dir`).
- Differential baseline vs candidate replay comparison (`--baseline-dir` + `--candidate-dir`).
- JSON report export for single-run mode (`--report-out`).

Examples:
- Single:
  - `python -m tools.engine_repro_lab.main --replay-json tools/data/replay/session.json --report-out tools/data/repro/report.json`
- Batch:
  - `python -m tools.engine_repro_lab.main --batch-dir tools/data/replay`
- Differential:
  - `python -m tools.engine_repro_lab.main --baseline-dir tools/data/replay_baseline --candidate-dir tools/data/replay_candidate`

# Engine Debug Tools Developer Guide

## Architecture
Tools are split into focused apps and a shared core:
- Shared core: `tools/engine_obs_core`
- Live triage: `tools/engine_monitor`
- Offline analysis: `tools/engine_session_inspector`
- Deterministic validation: `tools/engine_repro_lab`

Rule: parsing/normalization stays in `engine_obs_core`; UIs consume normalized models.

## Core modules
- `contracts.py`: canonical records and schema guards
- `datasource/file_source.py`: offline ingestion
- `datasource/live_source.py`: live polling adapter
- `query.py`, `timeline.py`, `aggregations.py`: analysis primitives
- `export.py`: report writing

## Test locations
- Core tests: `tests/tools/engine_obs_core`
- Monitor tests: `tests/tools/engine_monitor`
- Session Inspector tests: `tests/tools/engine_session_inspector`
- Repro Lab tests: `tests/tools/engine_repro_lab`

Performance budget checks are in:
- `tests/tools/engine_obs_core/test_performance_budgets.py`
- `tests/tools/engine_monitor/test_view_model_perf_budget.py`

## CI integration
Quality workflow (`.github/workflows/quality.yml`) includes a dedicated tools test job.
The job uses `PYTHONPATH=.` and runs:
```bash
uv run pytest tests/tools -q
```

## Extension workflow
1. Add/extend normalized models in `engine_obs_core`.
2. Add view-model logic in tool-specific `views/`.
3. Keep UI controls minimal by default.
4. Add tests for:
- correctness
- schema compatibility
- performance budget (if data volume path changed)

## Runbooks
1. Live hitch triage:
- Start `engine_monitor`
- locate top hitch in `Hitch Analyzer`
- inspect `Render/Resize` counts

2. Offline issue timeline:
- open `engine_session_inspector`
- select session
- narrow with Events filters/preset
- verify offenders in Profiling

3. Regression validation:
- run Repro Lab batch or differential mode
- attach generated report JSON to issue/PR

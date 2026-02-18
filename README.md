# Warships2

PyGFX-based Warships game running on an engine-hosted runtime.

## Run (Dev)

1. Create/sync env (uv): `uv sync --dev`
2. Run game: `uv run python -m warships.main`

## Build EXE (Windows)

1. Build: `.\scripts\build_exe.ps1`
2. Packaging docs: `docs/build_windows_exe.md`

## Quality Checks

1. Run full local gate: `.\scripts\check.ps1`
2. Equivalent manual commands:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy`
   - `uv run pytest tests/engine --cov=engine --cov-report=term-missing --cov-fail-under=75`
   - `uv run pytest tests/warships --cov=warships.game --cov-report=term-missing --cov-fail-under=75`
   - `uv run pytest tests/warships/unit/core tests/warships/unit/presets tests/warships/unit/app/services --cov=warships.game.core --cov=warships.game.presets --cov=warships.game.app.services --cov-report=term-missing --cov-fail-under=90`

## Runtime Env Files

Preferred split configuration:
- `.env.engine`: engine-owned settings (`ENGINE_*`)
- `.env.app`: app-owned settings (`WARSHIPS_*`, app logging)
- optional local overrides (gitignored):
  - `.env.engine.local`
  - `.env.app.local`

Load order (later wins):
1. `.env.engine`
2. `.env.engine.local`
3. `.env.app`
4. `.env.app.local`

Quick setup:
1. `Copy-Item .env.engine.example .env.engine`
2. `Copy-Item .env.app.example .env.app`

## Runtime Env Flags

Engine-owned:
- `ENGINE_WINDOW_MODE`: `windowed` | `maximized` | `fullscreen` | `borderless`
- `ENGINE_UI_ASPECT_MODE`: `contain` (default preserve) or other mode supported by runtime
- `ENGINE_LOG_LEVEL`: engine diagnostics/runtime log verbosity
- `ENGINE_DEBUG_METRICS`: `1` enables runtime metrics collection
- `ENGINE_DEBUG_OVERLAY`: `1` enables in-frame metrics overlay (toggle with `F3`)
- `ENGINE_DEBUG_UI_TRACE`: `1` enables UI trace diagnostics hooks
- `ENGINE_DEBUG_RESIZE_TRACE`: `1` enables resize diagnostics hooks
- `ENGINE_DEBUG_UI_TRACE_AUTO_DUMP`: `1` dumps recent UI trace buffer on anomalies
- `ENGINE_DEBUG_UI_TRACE_DUMP_DIR`: output directory for anomaly JSONL dumps

App-owned:
- `WARSHIPS_DEBUG_INPUT`: `1` enables input debug logs
- `WARSHIPS_DEBUG_UI`: `1` enables UI debug logs
- `WARSHIPS_LOG_LEVEL`: app log verbosity
- `WARSHIPS_APP_DATA_DIR`: optional unified app-data root override
- `WARSHIPS_LOG_DIR`: optional override for run log output directory
- `LOG_FORMAT`: `json` | `text`

Logging architecture:
- Engine provides logging API/pipeline (`engine.api.logging`).
- Warships configures that API for app policy (level/format/file sink).

Run logs:
- Default location: `<game_root>/appdata/logs`
  - source runs: `warships/appdata/logs`
- File model: one file per run (`warships_run_<timestamp>.jsonl`)

## Architecture Docs

- `docs/design.md`: current architecture and module ownership
- `docs/engine_generalization_plan.md`: next-phase generic engine evolution plan

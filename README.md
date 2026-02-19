# Warships2

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Nullpoint56/Warships2)

Warships game built on a reusable Python engine runtime (`engine/`) with game-specific logic in `warships/`.

## Repository Layout

- `engine/`: reusable runtime, rendering, input, diagnostics primitives.
- `warships/`: Warships game domain, app orchestration, UI composition.
- `tools/`: offline developer tools (diagnostics, analysis, repro workflows).
- `tests/`: engine and game test suites.
- `docs/`: architecture, operations, plans, diagnostics, and history.

## Quick Start

1. Install/sync dependencies:
   - `uv sync --dev`
2. Create env files:
   - `Copy-Item .env.engine.example .env.engine`
   - `Copy-Item .env.app.example .env.app`
3. Run the game:
   - `uv run python -m warships.main`

## Development Workflow

- Full local quality gate:
  - `uv run python scripts/check.py`
- Build Windows executable:
  - `.\scripts\build_exe.ps1`

## Documentation

- Docs hub:
  - `docs/README.md`
- Architecture:
  - `docs/architecture/system_overview.md`
  - `docs/architecture/import_boundaries.md`
- Runtime/build operations:
  - `docs/operations/runtime_configuration.md`
  - `docs/operations/windows_build.md`
- Diagnostics and observability:
  - `docs/diagnostics/README.md`
- Plans and progress history:
  - `docs/plans/README.md`
  - `docs/history/development_history.md`

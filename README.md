# Warships2

PyGFX-based Warships game running on an engine-hosted runtime.

## Run (Dev)

1. Create/sync env (uv): `uv sync --dev`
2. Run game: `uv run python -m warships.main`

## Build EXE (Windows)

1. Build: `.\scripts\build_exe.ps1`
2. Packaging docs: `docs/build_windows_exe.md`

## Runtime Env Flags

- `WARSHIPS_WINDOW_MODE`: `windowed` | `maximized` | `fullscreen` | `borderless`
- `WARSHIPS_UI_ASPECT_MODE`: `contain` (default preserve) or other mode supported by runtime
- `WARSHIPS_DEBUG_INPUT`: `1` enables input debug logs
- `WARSHIPS_DEBUG_UI`: `1` enables UI debug logs
- `LOG_LEVEL`, `LOG_FORMAT`: logging setup

## Architecture Docs

- `docs/design.md`: current architecture and module ownership
- `docs/engine_generalization_plan.md`: next-phase generic engine evolution plan

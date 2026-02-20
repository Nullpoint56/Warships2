# Runtime Configuration

This document owns runtime environment setup and key configuration knobs.

## Env Files

Preferred split:

- `.env.engine`: engine-owned settings (`ENGINE_*`)
- `.env.app`: app-owned settings (`WARSHIPS_*`, app logging)
- Optional local overrides (gitignored):
  - `.env.engine.local`
  - `.env.app.local`

Load order (later wins):

1. `.env.engine`
2. `.env.engine.local`
3. `.env.app`
4. `.env.app.local`

Bootstrap:

1. `Copy-Item .env.engine.example .env.engine`
2. `Copy-Item .env.app.example .env.app`

## Common Engine Flags

- `ENGINE_HEADLESS`: `0|1` (`1`, `true`, `yes`, `on` are truthy)
- `ENGINE_WINDOW_MODE`: `windowed` | `maximized` | `fullscreen` | `borderless`
- `ENGINE_UI_ASPECT_MODE`: aspect behavior mode (default `contain`)
- `ENGINE_LOG_LEVEL`: engine/runtime logging verbosity

Diagnostics-related:

- `ENGINE_METRICS_ENABLED`: enable runtime metrics collection
- `ENGINE_UI_OVERLAY_ENABLED`: enable in-frame metrics overlay (`F3` toggle)
- `ENGINE_PROFILING_ENABLED`: enable frame profiling payload emission
- `ENGINE_PROFILING_SAMPLING_N`: frame profiling sampling interval
- `ENGINE_INPUT_TRACE_ENABLED`: high-volume input event tracing
- `ENGINE_DIAGNOSTICS_ENABLED`: diagnostics hub master toggle
- `ENGINE_DIAGNOSTICS_PROFILING_MODE`: `off|light|timeline|timeline_sample`
- `ENGINE_DIAGNOSTICS_HTTP_ENABLED`: diagnostics HTTP bridge toggle

Headless and renderer initialization:

- When `ENGINE_HEADLESS` is enabled, runtime runs without creating a renderer/window frontend.
- When `ENGINE_HEADLESS` is disabled, wgpu initialization failures are hard startup failures.
- Non-headless startup failures include detailed diagnostics payloads (adapter/backend/surface/
  platform context and stack/exception details).

## Common App Flags

- `WARSHIPS_DEBUG_INPUT`: enable input debug logs
- `WARSHIPS_DEBUG_UI`: enable UI debug logs
- `WARSHIPS_LOG_LEVEL`: app log verbosity
- `WARSHIPS_APP_DATA_DIR`: app-data root override
- `WARSHIPS_LOG_DIR`: run-log directory override
- `LOG_FORMAT`: `json` | `text`

## Logging Model

- Engine provides logging API/pipeline (`engine.api.logging`).
- Warships supplies app logging policy (level/format/sinks).

Default run logs:

- `<repo>/warships/appdata/logs`
- One file per run: `warships_run_<timestamp>.jsonl`


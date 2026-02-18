# Engine Diagnostics Playbook

This playbook is the operational companion to `docs/engine_diagnostics_plan.md`.

## Primary Tooling

Use `tools/engine_observability.py` as the default diagnostics UI and session inspector.

## Scope

- Runtime metrics (`ENGINE_DEBUG_METRICS`)
- Debug overlay (`ENGINE_DEBUG_OVERLAY`)
- UI diagnostics trace (`ENGINE_DEBUG_UI_TRACE`, `ENGINE_DEBUG_RESIZE_TRACE`)
- UI diagnostics raw dump files (`ui_diag_run_*.jsonl`)

## Enable Diagnostics

Set:

- `ENGINE_DEBUG_METRICS=1`
- `ENGINE_DEBUG_OVERLAY=1`
- `ENGINE_DEBUG_UI_TRACE=1`
- `ENGINE_DEBUG_RESIZE_TRACE=1`
- `ENGINE_LOG_LEVEL=DEBUG`

Optional tuning:

- `ENGINE_DEBUG_UI_TRACE_SAMPLING_N=1`
- `ENGINE_DEBUG_UI_TRACE_LOG_EVERY_FRAME=1`
- `ENGINE_DEBUG_UI_TRACE_PRIMITIVES=1`
- `ENGINE_DEBUG_UI_TRACE_KEY_FILTER=`
  - Comma-separated key prefixes to reduce trace volume.

## Reproduce Known UI Instability

1. Start app in windowed mode.
2. Resize horizontally for several events.
3. Resize vertically for several events.
4. Move mouse across UI without clicking.
5. Observe if button geometry changes unexpectedly.

## Collect Artifacts

1. Keep engine debug logs from current run.
2. Save UI diagnostics JSONL dump.
3. Record short note with repro order (`X->Y->mouse` or `Y->X->mouse`).

## Runtime Policy

- Engine runtime emits raw diagnostics only.
- Engine does not classify UI anomalies at runtime.
- Post-processing tools/tests may compute app-specific heuristics from the raw dump.

## Baseline Fixture

Known-bad baseline trace fixture:

- `tests/engine/integration/fixtures/ui_diag_known_bad_resize_then_input.jsonl`

Use it to compare anomaly signatures and JSON shape when debugging regressions.

## Performance Verification

Run two short sessions of the same scene:

1. Diagnostics disabled:
   - `ENGINE_DEBUG_METRICS=0`
   - `ENGINE_DEBUG_OVERLAY=0`
   - `ENGINE_DEBUG_UI_TRACE=0`
   - `ENGINE_DEBUG_RESIZE_TRACE=0`
2. Diagnostics enabled:
   - `ENGINE_DEBUG_METRICS=1`
   - `ENGINE_DEBUG_OVERLAY=1`
   - `ENGINE_DEBUG_UI_TRACE=1`
   - `ENGINE_DEBUG_RESIZE_TRACE=1`

Compare:

- Rolling frame time (`FrameMs`) and FPS in overlay/logs
- Stability of frame pacing during resize/input interaction

Acceptance target:

- Disabled diagnostics path should stay effectively baseline.
- Enabled diagnostics path should remain bounded and not accumulate unbounded memory.

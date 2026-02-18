# Engine Diagnostics Playbook

This playbook is the operational companion to `docs/engine_diagnostics_plan.md`.

## Scope

- Runtime metrics (`ENGINE_DEBUG_METRICS`)
- Debug overlay (`ENGINE_DEBUG_OVERLAY`)
- UI diagnostics trace (`ENGINE_DEBUG_UI_TRACE`, `ENGINE_DEBUG_RESIZE_TRACE`)
- UI anomaly dump files (`ui_diag_run_*.jsonl`)

## Enable Diagnostics

Set:

- `ENGINE_DEBUG_METRICS=1`
- `ENGINE_DEBUG_OVERLAY=1`
- `ENGINE_DEBUG_UI_TRACE=1`
- `ENGINE_DEBUG_RESIZE_TRACE=1`
- `ENGINE_LOG_LEVEL=DEBUG`

Optional tuning:

- `ENGINE_DEBUG_UI_TRACE_SAMPLING_N=1`

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

## Expected Signatures

- `button_jitter:<id>`
  - Button transformed geometry changed without matching viewport revision change.
- `button_ratio_spread:<value>`
  - Sibling button height/text ratio diverged beyond threshold.

Interpretation:

- Source specs stable + jitter anomaly:
  - investigate input/invalidate/draw ordering and per-frame viewport revision.
- Ratio spread anomaly:
  - investigate sibling layout consistency and transform path.

## Baseline Fixture

Known-bad baseline trace fixture:

- `tests/engine/integration/fixtures/ui_diag_known_bad_resize_then_input.jsonl`

Use it to compare anomaly signatures and JSON shape when debugging regressions.

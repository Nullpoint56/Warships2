# Engine Diagnostics Plan (v0.5 -> v1.0)

## Goal
Build a minimal, engine-owned observability layer that:

- Improves runtime visibility before networking/audio integration.
- Diagnoses current UI instability (resize/mouse-move snap and inconsistent widget sizing).
- Stays non-invasive when disabled (near-zero overhead, no gameplay behavior change).
- Scales into future debugging needs without engine refactors.

## Execution Status

- Phase 1: Completed
- Phase 2: Completed
- Phase 3: Completed
- Phase 4: Completed
- Phase 5: Completed

This plan is implementation-focused and avoids blind iteration.

## Constraints

- Engine-layer only (no Warships domain coupling in metrics/debug core).
- Disabled path must not allocate or branch heavily in hot loops.
- No external profiler dependency.
- No deep inspector UI in this phase.
- Python standard library only for timing/logging/collections.

## Deliverables

1. `engine.runtime.metrics` collector module.
2. Update loop instrumentation with per-system timings.
3. Scheduler/event counters.
4. Lightweight debug overlay renderer in engine UI runtime.
5. UI rendering diagnostics for resize/layout instability.
6. Unified logging discipline and env-configurable log levels.
7. Test coverage for enabled/disabled modes and UI diagnostics.
8. Documentation for flags, usage, and troubleshooting workflow.

---

## 1) Runtime Debug Configuration

### New module
- `engine/runtime/debug_config.py`

### Responsibilities
- Parse and expose immutable debug settings from env vars:
  - `ENGINE_DEBUG_METRICS=0|1`
  - `ENGINE_DEBUG_OVERLAY=0|1`
  - `ENGINE_DEBUG_UI_TRACE=0|1`
  - `ENGINE_DEBUG_UI_TRACE_SAMPLING_N=1..N` (default 10)
  - `ENGINE_DEBUG_RESIZE_TRACE=0|1`
  - `ENGINE_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`
- Provide helpers:
  - `enabled_metrics()`
  - `enabled_overlay()`
  - `enabled_ui_trace()`
  - `enabled_resize_trace()`

### Acceptance
- Single source of truth for debug flags.
- No direct `os.getenv(...)` calls scattered in runtime systems.

---

## 2) Metrics Core

### New module
- `engine/runtime/metrics.py`

### Data model
- `FrameMetrics`:
  - `frame_index: int`
  - `dt_ms: float`
  - `fps_rolling: float`
  - `scheduler_queue_size: int`
  - `event_publish_count: int`
  - `system_timings_ms: dict[str, float]`
- `MetricsSnapshot`:
  - `last_frame: FrameMetrics | None`
  - `rolling_dt_ms: float`
  - `rolling_fps: float`
  - `top_systems_last_frame: list[tuple[str, float]]`

### Collector behavior
- Ring buffers for frame dt and fps (default window: 60 frames).
- Per-frame timing map reset each frame.
- O(1) insert/update operations.
- Snapshot generation only when requested (overlay/logging).

### Disabled mode behavior
- `NoopMetricsCollector` with identical API and no work.

### Acceptance
- Metrics can be enabled/disabled from config without call-site complexity.
- Snapshot stable and deterministic for tests.

---

## 3) UpdateLoop Instrumentation

### Target module
- `engine/gameplay/update_loop.py` (or equivalent existing update loop module)

### Instrumentation points
- At frame start:
  - capture `frame_start = time.perf_counter()`
  - `metrics.begin_frame(frame_index)`
- For each `GameplaySystem` execution:
  - `sys_start = time.perf_counter()`
  - execute
  - `metrics.record_system_time(system_name, elapsed_ms)`
- At frame end:
  - record total frame dt
  - finalize fps rolling stats

### Error path handling
- If system throws, still record partial timing + exception count.
- No swallowed exceptions; behavior unchanged.

### Acceptance
- Per-system timings visible in metrics snapshot and overlay.
- Update loop semantics unchanged.

---

## 4) Scheduler and Event Counters

### Target modules
- `engine/runtime/scheduler.py`
- event bus/publisher module (`engine/runtime/events.py` or equivalent)

### Instrumentation
- Scheduler:
  - record queue length at frame boundary.
  - optional counters for enqueued/dequeued per frame.
- Event bus:
  - increment publish count per frame.
  - optional per-topic counts (kept off by default).

### Acceptance
- Overlay shows scheduler queue size.
- Metrics snapshot includes publish count.

---

## 5) Lightweight Debug Overlay

### New module
- `engine/ui_runtime/debug_overlay.py`

### Rendered content (dev-only)
- `FPS` and rolling frame time (`ms`).
- Top 3 slowest systems (last frame).
- Scheduler queue size.
- Event publish count.
- Optional UI diagnostics row (if UI trace enabled):
  - viewport revision
  - resize seq
  - raw trace status/count

### Integration point
- Runtime frame orchestration after normal game render call.
- Overlay uses existing `RenderAPI` (`add_rect`, `add_text`), engine-generic keys.

### Toggle behavior
- Env toggle required for now: `ENGINE_DEBUG_OVERLAY=1`.
- Optional runtime key toggle can be phase 2 if input path is already generic.

### Acceptance
- Overlay hidden by default.
- No warships-specific labels/logic inside overlay module.

---

## 6) Logging Discipline

### Logger namespaces
- `engine.runtime`
- `engine.update`
- `engine.rendering`
- `engine.ui_runtime`
- Reserved for future:
  - `engine.network`
  - `engine.audio`

### Policy
- Replace ad-hoc prints with structured `logger.debug/info`.
- Standard message keys for high-volume traces:
  - `frame_metrics`
  - `system_timing`
  - `resize_event`
  - `ui_projection`
  - `ui_button_geometry`

### Config
- Initialize log level from `ENGINE_LOG_LEVEL`.

### Acceptance
- Consistent categories and message style across runtime components.

---

## 7) UI-Specific Diagnostics (Root-Cause Stack)

This section is mandatory to solve the current instability class.

### New module
- `engine/rendering/ui_diagnostics.py`

### Captured signals (per frame, sampled)
- Canvas/event sizes:
  - raw resize payload values (`width/height`, `size`, `logical_size`, `physical_size` when present)
  - applied renderer size
- Viewport transform:
  - `sx`, `sy`, `ox`, `oy`, `viewport_revision`
- Button geometry per id:
  - source rect (`x,y,w,h` in design space)
  - transformed rect (`tx,ty,tw,th`)
  - text size used (`tsize`)
  - text-to-rect ratio for sanity
- Input-triggered redraw markers:
  - pointer move/release timestamps
  - frame reason (`resize`, `input`, `scheduler`, `manual invalidate`)

### Engine-side diagnostics policy
- Engine runtime emits raw diagnostics only.
- Soft heuristics and anomaly classification are post-processing concerns and must live
  in app/test analysis tools.

### Output strategy
- By default: ring buffer in memory (last 300 frames).
- Optional file dump when anomaly detected:
  - `logs/ui_diag_<timestamp>.jsonl`

### Acceptance
- When issue reproduces, diagnostics can answer:
  - Did source button specs change?
  - Did transform inputs change?
  - Did transformed geometry diverge across siblings?
  - Was the triggering frame resize-driven or input-driven?

---

## 8) Test Plan

### Unit tests
- `tests/engine/unit/runtime/test_metrics.py`
  - rolling averages, top-3 extraction, disabled no-op behavior.
- `tests/engine/unit/gameplay/test_update_loop_metrics.py`
  - per-system timing capture.
- `tests/engine/unit/runtime/test_scheduler_metrics.py`
  - queue size metrics update.
- `tests/engine/unit/ui_runtime/test_debug_overlay.py`
  - formatting, empty snapshot behavior, toggle behavior.
- `tests/engine/unit/rendering/test_ui_diagnostics.py`
  - invariant detection and anomaly dump trigger.

### Integration tests
- `tests/engine/integration/test_diagnostics_disabled_parity.py`
  - confirm behavior parity with diagnostics off.
- `tests/engine/integration/test_resize_diagnostics_pipeline.py`
  - simulated resize + pointer sequence emits complete trace set.

### Performance checks
- diagnostics off:
  - <1% frame-time overhead.
- diagnostics on:
  - bounded allocations via ring buffers.

---

## 9) Rollout Plan (Exact Sequence)

### Phase 1: Foundation
- Add `debug_config.py`, `metrics.py`, noop collector.
- Wire config bootstrap and logger level.
- Add unit tests for metrics and config.

### Phase 2: Runtime Instrumentation
- Instrument update loop, scheduler, event counters.
- Add runtime metrics tests.
- Ensure disabled-path parity tests pass.

### Phase 3: Overlay
- Implement `debug_overlay.py`.
- Integrate overlay draw in runtime frame flow.
- Add overlay tests.

### Phase 4: UI Diagnostics Stack
- Add `ui_diagnostics.py` and hooks in rendering/input/update boundaries.
- Add invariant detector(s) and anomaly JSONL dump path.
- Add focused UI diagnostics tests.

### Phase 5: Debug Playbook
- Add troubleshooting procedures and expected signatures.
- Capture one known-bad resize reproduction trace as baseline fixture.

---

## 10) Troubleshooting Playbook (Operational)

### Flags for current UI issue
- `ENGINE_DEBUG_METRICS=1`
- `ENGINE_DEBUG_OVERLAY=1`
- `ENGINE_DEBUG_UI_TRACE=1`
- `ENGINE_DEBUG_RESIZE_TRACE=1`
- `ENGINE_LOG_LEVEL=DEBUG`

### Repro protocol
1. Launch in windowed mode.
2. Resize Y until stable stretch.
3. Move mouse to trigger snap.
4. Resize X and repeat.
5. Export anomaly trace JSONL.

### Decision tree
- If source button specs changed unexpectedly:
  - investigate controller/UI button composition.
- If source stable but transformed diverges:
  - investigate viewport/revision/update ordering.
- If divergence appears only on input-driven frames:
  - inspect input->invalidate->render ordering.
- If divergence aligns with backend size jitter:
  - backend/resize adapter workaround path.

---

## Acceptance Criteria

- Warships runs unchanged with diagnostics disabled.
- Diagnostics enabled provides stable metrics and overlay.
- Per-system timings visible each frame.
- Scheduler and event counters are captured.
- UI diagnostics can localize current resize/button instability to a concrete stage.
- All diagnostics are engine-owned and reusable for networking/audio era.

---

## Out of Scope (for this plan)

- Packet inspector
- Timeline visualizer
- Visual state inspector
- ECS tools
- External profiler integration
- Engine architecture rewrite

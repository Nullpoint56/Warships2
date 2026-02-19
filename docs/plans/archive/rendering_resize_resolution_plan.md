# Rendering Resize Resolution Plan

Date: 2026-02-18  
Scope: `engine/rendering/*`, `engine/runtime/*`, diagnostics tooling  
Status: Draft for execution

## Objective

Resolve interactive resize artifacts in the pygfx + rendercanvas path using evidence-first diagnostics, then minimal-risk fixes, before any renderer replacement decision.

## Problem Statement

During live window resizing, rendered geometry can appear to hold and jump, stretch, or catch up one frame later. The current code path mixes event-driven and polled size updates, applies integer quantization, and relies on draw-loop scheduling for visible updates.

## Evidence Already Confirmed

1. Size is applied from both resize events and per-frame sync.
2. `_apply_canvas_size()` truncates with `int(width)` and `int(height)`.
3. `_on_resize()` updates projection state without explicit redraw request.
4. Camera projection uses width/height fields and transform update; no `set_view_size(...)`.
5. Text and geometry use different coordinate spaces (`screen_space=True` for text).
6. Mid-frame consistency is intentionally snapshot-based and can yield one-frame catch-up.
7. Diagnostics already capture resize payloads, viewport revision, and renderer/canvas size telemetry.

## Success Criteria

1. No visible persistent stretch during active drag-resize in windowed mode.
2. Resize-to-draw latency remains bounded to at most one frame for normal interaction.
3. No regressions in retained/static primitive behavior across resize + input sequences.
4. Existing diagnostics remain bounded in memory and disabled-path parity is preserved.

## Non-Goals

1. Replacing pygfx/wgpu/rendercanvas stack in this effort.
2. Building a full GPU capture automation pipeline in this phase.
3. Rewriting retained rendering architecture.

## Execution Phases

### Phase 0: Baseline and Repro Contract

Goal: lock a deterministic repro protocol and artifact format before changes.

Steps:

1. Use existing flags:
   - `ENGINE_DEBUG_UI_TRACE=1`
   - `ENGINE_DEBUG_RESIZE_TRACE=1`
   - `ENGINE_DEBUG_UI_TRACE_SAMPLING_N=1`
2. Reproduce using fixed sequence:
   - horizontal drag burst
   - vertical drag burst
   - pointer move without click
3. Save JSONL trace and runtime logs.
4. Record exact environment tuple:
   - OS version
   - GPU + driver
   - `pygfx`, `wgpu`, `rendercanvas` versions

Exit criteria:

1. At least one reproducible trace with observed artifact.
2. Repro notes include exact ordered interaction steps and environment tuple.

Deliverables:

1. Trace artifact under diagnostics dump path.
2. One short repro note attached to issue thread.

---

### Phase 1: Instrumentation Hardening

Goal: add timing and version metadata needed to classify fault class quickly.

Implementation targets:

1. `engine/rendering/ui_diagnostics.py`
2. `engine/rendering/scene.py`
3. `engine/runtime/debug_config.py` (if new flags are needed)

Additions:

1. Event-to-draw latency stamps:
   - `resize_event_ts`
   - `size_applied_ts`
   - `frame_render_ts`
2. Frame-level version stamp:
   - runtime backend name when available
   - dependency versions (`pygfx`, `wgpu`, `rendercanvas`)
3. Optional compact state markers:
   - `ui_state_revision`
   - `ui_state_hash` (only if cheap and deterministic)

Exit criteria:

1. Trace can distinguish scheduling lag vs size-source mismatch vs backend target lag.
2. Added diagnostics do not change behavior when disabled.

Tests:

1. Extend `tests/engine/unit/rendering/test_ui_diagnostics.py` for new payload shape.
2. Extend `tests/engine/integration/test_resize_diagnostics_pipeline.py` with latency/version fields.
3. Confirm `tests/engine/integration/test_diagnostics_disabled_parity.py` remains green.

---

### Phase 2: Single-Variable Experiment Matrix

Goal: isolate dominant fault contributor with minimal, reversible patches.

Run experiments one variable at a time:

1. Force redraw on resize handler:
   - add `invalidate()` at end of `_on_resize()`.
2. Size quantization policy trial:
   - compare truncation vs explicit rounding strategy.
3. Single source of truth trial:
   - event-only size path.
   - frame-sync-only size path.
4. Camera API trial:
   - guarded `set_view_size(...)` if supported by installed pygfx.

For each run capture:

1. artifact severity (none/minor/major)
2. resize-to-draw latency distribution
3. mismatch counters:
   - event size vs applied size
   - canvas size vs renderer target
4. regression notes for input/layout behavior

Exit criteria:

1. One or two dominant contributors identified with evidence.
2. At least one patch candidate demonstrates clear improvement without obvious regressions.

Deliverables:

1. Experiment table committed to this doc or companion issue note.

---

### Phase 3: Candidate Fix Implementation

Goal: land minimal production fix set from Phase 2 findings.

Selection rules:

1. Prefer the smallest fix that satisfies success criteria.
2. Avoid backend-specific branching unless strictly required.
3. Keep current diagnostics architecture and disabled fast path.

Likely fix classes:

1. redraw scheduling improvement (`invalidate` on resize)
2. deterministic size policy cleanup
3. unified size source ordering
4. camera view update compatibility shim

Implementation targets:

1. `engine/rendering/scene.py`
2. `engine/rendering/scene_viewport.py` (if extraction/normalization changes)
3. `engine/runtime/pygfx_frontend.py` (only if mode-specific invalidation is needed)

Exit criteria:

1. Success criteria met on baseline repro environment.
2. No failures in existing unit/integration rendering tests.

---

### Phase 4: Regression Net Expansion

Goal: prevent recurrence with targeted automated coverage.

Required additions:

1. unit tests for chosen quantization and size-source policy.
2. integration test for resize burst + pointer sequence ensuring stable geometry revision progression.
3. fixture update if known-bad signature changes.

Targets:

1. `tests/engine/unit/rendering/test_scene_graphics.py`
2. `tests/engine/unit/rendering/test_scene_viewport.py`
3. `tests/engine/integration/test_resize_diagnostics_pipeline.py`
4. `tests/engine/integration/fixtures/ui_diag_known_bad_resize_then_input.jsonl` (only if needed)

Exit criteria:

1. New tests fail without fix and pass with fix.
2. CI runtime remains acceptable.

---

### Phase 5: Optional Deep Diagnostics Burst

Goal: only if issue remains partially unresolved, add higher-tier state reconstruction.

Additions (gated by debug flags):

1. `ENGINE_DEBUG_UI_STATE_TRACE`
2. `ENGINE_DEBUG_UI_STATE_FULL_BURST_FRAMES`
3. `ENGINE_DEBUG_UI_STATE_MAX_BYTES`

Payload extensions:

1. `ui_state.revision`
2. `ui_state.hash`
3. optional `ui_state.delta`
4. `ui_snapshot` records for burst frames

Exit criteria:

1. Full snapshot + delta replay can reconstruct frame state and verify hash continuity.
2. Memory and payload size remain bounded by configured caps.

---

### Phase 6: Decision Gate (Keep Stack vs Escalate)

Goal: make renderer strategy decision based on evidence, not frustration.

Decision rules:

1. If first bad frame is incorrect in app/render diagnostics, continue internal fixes.
2. If diagnostics state is correct but on-screen output diverges, escalate to backend/GPU-level investigation.
3. Consider renderer replacement only if repeated backend limitations remain unresolved after targeted fixes.

Escalation path:

1. enable verbose backend logging categories
2. run short platform GPU capture on failing resize window
3. compare with internal trace timestamps and size lineage

## Risk Register

1. Over-instrumentation hides race/scheduling behavior by changing timing.
   - Mitigation: keep trace sampling/configurable, validate with diagnostics disabled.
2. Backend/version variance leads to non-reproducible conclusions.
   - Mitigation: stamp environment tuple in every artifact.
3. Broad fix accidentally regresses input-driven redraw behavior.
   - Mitigation: integration test for resize + pointer sequencing.

## Work Breakdown (Suggested)

1. Instrumentation hardening and tests (Phase 1)
2. Experiment matrix runs and evidence table (Phase 2)
3. Minimal fix landing with tests (Phases 3-4)
4. Optional deep diagnostics only if still unresolved (Phase 5)

## Exit Conditions for This Initiative

1. Resize behavior is stable across baseline repro and at least one secondary environment.
2. Diagnostics can identify first divergence frame and classify root-cause class.
3. Follow-up maintenance burden is low and bounded by current diagnostics architecture.

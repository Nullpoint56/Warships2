# Rendering Mode Migration Plan

Date: 2026-02-18  
Scope: Rendering loop scheduling and synchronization behavior  
Goal: Migrate from on-demand rendering to continuous-capable modes with non-blocking frame sync.

## Objective

Reduce resize artifacts and improve runtime smoothness by introducing configurable continuous rendering modes, while preserving stability, input responsiveness, and predictable resource usage.

## Current State

- Runtime primarily relies on on-demand draw invalidation.
- Resize diagnostics indicate app-side sizing/projection updates are fast and coherent.
- Prior resize-focused experiments did not eliminate visible artifact severity.
- This suggests scheduling/presentation behavior is a key lever to test for engine evolution.

## Success Criteria

1. Visible resize artifacts are reduced versus current on-demand baseline.
2. No regression in input responsiveness or UI interaction correctness.
3. No unbounded frame scheduling behavior (no draw storm loops).
4. Idle and interaction resource usage stay within acceptable budget.
5. Existing behavior can be restored by configuration toggle.

## Non-Goals

1. Immediate backend API rewrite.
2. Permanent removal of on-demand mode.
3. Replacing diagnostics stack during this migration.

## Phase Plan

### Phase 0: Baseline and Guardrails

#### Work

1. Lock a baseline run profile and repro gesture sequence.
2. Define target quality bar:
   - artifact severity threshold
   - acceptable input latency
   - acceptable idle/active frame pacing behavior
3. Ensure migration is feature-flagged and reversible.

#### Exit Criteria

1. Baseline traces and notes are captured.
2. Rollback path is explicit and tested.

---

### Phase 1: Configuration Surface

#### Work

Add rendering mode controls:

1. `on_demand` (current behavior)
2. `continuous`
3. `continuous_during_resize`

Add sync controls:

1. target FPS cap (e.g. 60, 120)
2. non-blocking pacing policy (time-based frame throttling)

#### Exit Criteria

1. Config parsing is deterministic and validated in tests.
2. Invalid config values fail safely to baseline defaults.

---

### Phase 2: Loop Controller Refactor

#### Work

1. Isolate scheduling logic into a loop controller abstraction.
2. Keep draw pipeline and scene update logic unchanged.
3. Add backpressure controls:
   - do not queue unlimited draws
   - avoid duplicate pending frame requests

#### Exit Criteria

1. On-demand path behavior remains parity-equivalent.
2. No blocking waits on the UI thread from loop controller.

---

### Phase 3: Continuous Mode Implementation

#### Work

1. Implement always-on continuous rendering mode.
2. Apply non-blocking sync using frame-time pacing and cap.
3. Preserve invalidate compatibility for existing callers.

#### Exit Criteria

1. Continuous mode runs stably with predictable pacing.
2. No runaway CPU usage due to uncontrolled loop churn.

---

### Phase 4: Hybrid Mode (Recommended Candidate)

#### Work

Implement `continuous_during_resize`:

1. enter continuous mode on resize activity
2. maintain continuous mode through a configurable cooldown period
3. return to on-demand outside resize window

#### Exit Criteria

1. Resize interaction is smoother than baseline.
2. Idle overhead is significantly lower than always-continuous mode.

---

### Phase 5: Diagnostics Extensions

#### Work

Add loop diagnostics fields:

1. effective mode per frame
2. frame interval and pacing deltas
3. skipped/deferred scheduling counters
4. resize-window active marker and transition events

Tooling updates:

1. expose mode transitions and pacing summary in diagnostics tools
2. allow side-by-side run comparison by mode

#### Exit Criteria

1. Traces clearly show scheduler behavior and transitions.
2. Tooling can compare baseline vs new mode without manual parsing.

---

### Phase 6: Tests

#### Work

Unit tests:

1. mode selection and defaults
2. pacing math and cap behavior
3. resize-window transition logic

Integration tests:

1. input remains responsive in continuous and hybrid modes
2. resize projection consistency under all modes
3. on-demand parity remains intact

#### Exit Criteria

1. New loop logic has deterministic automated coverage.
2. Existing rendering diagnostics tests remain green.

---

### Phase 7: Controlled Rollout

#### Work

1. Land feature behind config with baseline default (`on_demand`).
2. Run team test matrix on target machines.
3. Promote default to `continuous_during_resize` only if metrics and UX improve.
4. Keep `continuous` as opt-in high-throughput mode.

#### Exit Criteria

1. Rollout decision is evidence-backed from traces and test notes.
2. Revert toggle remains available in production builds.

---

### Phase 8: Decision Gate

#### Work

1. If new loop modes significantly reduce artifacts, harden and keep.
2. If not, escalate to backend/presentation-specific strategy with gathered evidence.

#### Exit Criteria

1. Clear recorded decision: adopt mode change or proceed with backend-specific mitigation.

## Implementation Notes

1. Prefer incremental PR-sized changes per phase.
2. Keep defaults conservative until validation is complete.
3. Avoid long-running shell/watch commands during implementation and validation.

## Proposed Execution Order

1. Phase 1 + Phase 2
2. Phase 4 (hybrid) before Phase 3 (always continuous)
3. Phase 5 + Phase 6
4. Phase 7 rollout decision

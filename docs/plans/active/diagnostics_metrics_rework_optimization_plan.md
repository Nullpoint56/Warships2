# Diagnostics Metrics Rework + Optimization Plan

Date: 2026-02-21
Status: Active
Scope: Rework engine diagnostics data model and reduce runtime overhead while preserving actionable profiling workflows.

## Why This Plan Exists

Current diagnostics are useful but too costly and structurally inconsistent for long-term profiling:

1. Data schema drift
- Mixed payload shapes across `frame`, `render`, `perf`, `scheduler`, `input` events.
- Tooling relies on implicit keys instead of explicit schema contracts.

2. Runtime overhead
- High-frequency event emission in hot paths.
- Repeated dict cloning/serialization-heavy payloads.
- Debug/profiling modes can materially affect measured FPS.

3. Tooling friction
- Live monitor polling/snapshot UX and data coupling make bottleneck isolation harder than needed.

## Goals

1. Establish a stable, versioned diagnostics schema for live + export paths.
2. Make low-overhead profiling the default for development profiling runs.
3. Keep deep diagnostics available behind explicit high-cost modes.
4. Ensure profiling instrumentation does not materially distort frame timing in target scenes.

## Non-Goals

1. No gameplay/UI feature work.
2. No renderer visual changes.
3. No Warships-only diagnostic hacks.

## Design Principles

1. Schema first: every public diagnostics payload must be versioned.
2. Cost explicitness: every high-cost metric path must be opt-in.
3. Single producer contract: engine owns canonical event schemas; tools consume, not infer.
4. Progressive detail: cheap aggregates first, expensive detail on demand.

## Target Architecture

1. Canonical stream layers
- `diag.frame.v2`: compact per-frame aggregate record.
- `diag.render.v2`: compact renderer block profile + execute summary.
- `diag.system.v2`: optional sampled system timing detail.
- `diag.span.v2`: optional timeline spans (high-cost mode).

2. Mode presets (engine-owned)
- `off`: minimal/none.
- `fast_profile`: compact frame/render aggregates only.
- `balanced_profile`: fast profile + sampled system detail.
- `deep_trace`: full spans + topic/system breakdown + replay/crash extras.

3. Snapshot endpoints
- `/metrics`: latest compact aggregates only.
- `/snapshot`: bounded recent canonical events (filtered by mode).
- `/profiling`: span-oriented data only (when enabled).

## Execution Phases

### Phase 1: Schema Contract + Event Catalog

Implementation:
1. Define versioned schema dataclasses/contracts for frame/render/system/span payloads.
2. Add schema version constants and compatibility notes.
3. Map current emitted event names to canonical v2 names.
4. Add schema validation tests for emitted payloads.

Exit:
1. Canonical diagnostics event catalog documented in code and tests.
2. Tools can consume via explicit schema fields, not ad hoc key lookups.

### Phase 2: Producer Refactor (Low-Overhead Core)

Implementation:
1. Replace heavy per-frame payload construction with compact aggregate builders.
2. Remove default full-map cloning (`timings_ms`, per-topic maps) from hot path.
3. Gate detailed maps behind explicit high-detail toggles.
4. Introduce lightweight object reuse where safe in diagnostics producers.

Exit:
1. `fast_profile` mode emits only compact frame/render records.
2. Profiling overhead in idle/menu scenes is significantly reduced versus current debug profile.

### Phase 3: Preset System + Config Cleanup

Implementation:
1. Introduce one authoritative diagnostics mode env (`ENGINE_DIAGNOSTICS_MODE_PRESET`).
2. Resolve and apply derived toggles internally (single source of truth).
3. Remove obsolete/duplicative flags and dead code paths.
4. Keep optional advanced overrides for temporary experiments only.

Exit:
1. Run configs switch by preset rather than large env flag bundles.
2. Toggle surface area is reduced and documented.

### Phase 4: HTTP + Live Monitor Contract Split

Implementation:
1. Ensure `/metrics` returns compact model only (no heavy arrays/maps).
2. Add optional query flags for deep detail (`?detail=system`, `?detail=topics`) with strict limits.
3. Update live monitor to prefer compact endpoints and incremental refresh behavior.
4. Ensure monitor avoids full-text redraw when no relevant model change.

Exit:
1. Live monitor remains responsive with minimal observer effect.
2. Copy/export workflows still provide full detail when explicitly requested.

### Phase 5: Validation + Budget Enforcement

Implementation:
1. Add profiling overhead benchmark checks in representative Warships scenes.
2. Add guardrails that fail tests if fast-profile payload grows beyond budget.
3. Add docs/runbook for choosing presets and reading bottleneck outputs.

Exit:
1. Diagnostics overhead budget is measurable and enforced.
2. Team can reliably profile without large measurement distortion.

## Suggested Initial Budgets

1. `fast_profile` target overhead: <= 5% frame-time impact in menu/list scenes.
2. `balanced_profile` target overhead: <= 12% frame-time impact.
3. `deep_trace` may exceed budgets but must be explicit and non-default.

## Acceptance Criteria

1. Schema:
- Versioned canonical payloads used by engine and monitor.

2. Performance:
- Fast profiling mode no longer causes major FPS collapse versus non-debug runs.

3. Tooling:
- Live monitor supports compact-first reads and optional deep detail.

4. Maintainability:
- Diagnostics toggle/config surface is smaller and clearer.

## Risks

1. Tool breakage during schema migration.
Mitigation: dual-read adapters during transition window.

2. Hidden reliance on old event names/fields.
Mitigation: migration tests covering monitor/view-model parsing.

3. Premature toggle removal.
Mitigation: remove only after code-path usage audit + test coverage.

## Immediate Next Step

1. Execute Phase 1 and produce `diagnostics_schema_v2.md` + payload contract tests.

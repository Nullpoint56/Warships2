# Engine Policy Migration Plan

Date: 2026-02-19  
Scope: Input policies, Rendering policies, Window & Panel policies  
Sources:
- `docs/architecture/input_policies.md`
- `docs/architecture/rendering_policies.md`
- `docs/architecture/window_and_panel_policies.md`

## Purpose

Migrate the engine to comply with all three policy documents with minimal disruption, explicit phase gates, and testable outcomes.

## Current Gap Snapshot

- Input is event-drain driven, not immutable per-frame snapshot driven (`engine/runtime/pygfx_frontend.py`, `engine/input/input_controller.py`).
- Game module still consumes raw input events and renders inside frame update (`engine/api/game_module.py`, `warships/game/app/engine_game_module.py`).
- Renderer owns canvas/window lifecycle and backend loop (`engine/rendering/scene.py`), and GLFW window operations sit in rendering helpers (`engine/rendering/scene_runtime.py`).
- No explicit `RenderSnapshot` handoff contract between simulation and renderer.
- Diagnostics are strong in rendering/host, but policy-required input/window diagnostics are only partial.

## Phase Plan

## Phase 0: Baseline and Policy Matrix

### Work

1. Create a requirement matrix mapping each policy clause to current code ownership and status (`Compliant`, `Partial`, `Gap`).
2. Capture baseline behavior:
   - input flow
   - resize flow
   - replay payload shape
   - frame lifecycle behavior
3. Define migration guardrails and rollback points.

### Exit Criteria

1. Matrix is documented and committed.
2. Baseline evidence is available for regression checks.

---

## Phase 1: Add New Engine Contracts (Compatibility Stage)

### Work

1. Add `InputSnapshot` API (immutable frame input contract), e.g. new `engine/api/input_snapshot.py`.
2. Add `WindowPort`/`SurfaceHandle`/normalized window event API, e.g. new `engine/api/window.py`.
3. Add `RenderSnapshot` API, e.g. new `engine/api/render_snapshot.py`.
4. Extend `GameModule` API with next-gen hooks while keeping current hooks temporarily for compatibility:
   - `on_input_snapshot(...)`
   - `simulate(...)`
   - `build_render_snapshot(...)`

### Exit Criteria

1. New contracts compile and are covered by basic contract tests.
2. Existing runtime path remains functional (no behavior change yet).

---

## Phase 2: Extract Window/Panel Subsystem

### Work

1. Create `engine/window/` package owning:
   - OS window lifecycle
   - event loop polling
   - DPI/resize/focus/minimize events
   - surface provisioning for renderer
2. Move startup window mode and backend window operations out of rendering helpers.
3. Update runtime composition (`engine/runtime/bootstrap.py`) to dependency direction:
   - `WindowLayer -> Surface -> RenderBackend`

### Exit Criteria

1. Renderer no longer creates/owns OS window lifecycle.
2. Window backend details do not leak into engine core APIs.

---

## Phase 3: Deterministic Input Snapshot Pipeline

### Work

1. Introduce frame-based input pipeline:
   - collect raw events from window layer
   - normalize by device type
   - resolve action map
   - publish immutable `InputSnapshot` per frame
2. Replace direct event-drain dispatch path in frontend runtime.
3. Ensure no mid-frame input mutation visible to simulation.

### Exit Criteria

1. Simulation consumes only frame-stable input snapshots.
2. Input backend remains replaceable and isolated.

---

## Phase 4: Action Mapping and Replay Compliance

### Work

1. Centralize mapping `physical input -> logical action` in engine input subsystem.
2. Update replay capture to record logical action stream (or snapshot-derived actions), not raw backend events.
3. Add diagnostics for:
   - event frequency
   - mapping conflicts
   - device connect/disconnect

### Exit Criteria

1. Replay can drive simulation deterministically without physical device state.
2. Action rebinding path is explicit and tested.

---

## Phase 5: Simulation/Rendering Decoupling via RenderSnapshot

### Work

1. Refactor frame contract to:
   1. `simulate()`
   2. `build_snapshot()`
   3. `renderer.render(snapshot)`
2. Split Warships module flow so simulation update does not directly render.
3. Add snapshot builder path for UI/world draw data.
4. Define snapshot granularity rule in contract and tests:
   - snapshot carries final world transforms
   - renderer performs no gameplay transform computation
   - renderer remains passive and visual-only

### Exit Criteria

1. Renderer consumes immutable snapshot only.
2. Renderer does not read or mutate live simulation state.

---

## Phase 6: Explicit Renderer Lifecycle and Pass Pipeline

### Work

1. Make renderer lifecycle explicit:
   1. `begin_frame()`
   2. build batches
   3. execute passes
   4. `present()`
   5. `end_frame()`
2. Keep mixed-mode support:
   - retained mode
   - immediate mode merged into batch stage
3. Prepare multi-pass structure:
   - world/geometry pass
   - overlay/UI pass
   - future post-process slot

### Exit Criteria

1. Lifecycle stages are explicit in code and diagnostics.
2. Single-pass default works through the same staged pipeline.

---

## Phase 7: Rendering Policy Hardening

### Work

1. Enforce deterministic ordering with explicit stable layer sort.
2. Introduce dimension-neutral snapshot/model conventions (`Vec3`/`Mat4`-style transform data model).
3. Enforce color space policy:
   - linear internal math
   - sRGB presentation at swapchain/output
4. Keep resize deterministic:
   - surface reconfigure
   - projection/viewport update
   - no unnecessary device recreation
5. Enforce frame concurrency baseline:
   - one frame in flight in initial implementation
   - no manual GPU fence synchronization unless profiling evidence requires it
6. Enforce renderer asset ownership boundary:
   - renderer consumes handles or immutable references only
   - asset I/O remains in dedicated asset subsystem

### Exit Criteria

1. Ordering/color/resize rules are enforced and test-covered.
2. 2D remains stable while enabling additive path to 3D.
3. One-frame-in-flight behavior is documented and verified by tests/diagnostics.
4. Renderer performs no asset loading I/O in runtime path.

---

## Phase 8: Diagnostics, Thread Readiness, and Cleanup

### Work

1. Complete structured diagnostics coverage:
   - window: resize, DPI, focus, minimize/restore
   - input: rates, conflicts, device changes
   - rendering: frame begin/end, pass metrics, present timing, batching stats
2. Add snapshot handoff readiness for future render-thread move (double-buffer or atomic swap model).
3. Remove deprecated raw-event/legacy hooks after parity validation.

### Exit Criteria

1. Only policy-compliant architecture remains in active runtime path.
2. No required policy behavior depends on legacy compatibility path.

---

## Detailed Code Work Map by Phase

## Phase 0: Baseline and Policy Matrix

1. Add policy matrix table and code references to this plan.
2. Record baseline flow references:
   - input ingestion and draining in `engine/input/input_controller.py` and `engine/runtime/pygfx_frontend.py`
   - host frame loop in `engine/runtime/host.py`
   - current renderer loop and resize behavior in `engine/rendering/scene.py`
3. Add baseline assertions in tests before refactors:
   - existing input unit tests remain green
   - existing rendering integration diagnostics remain green

## Phase 1: Add New Engine Contracts (Compatibility Stage)

1. Add API contracts:
   - `engine/api/input_snapshot.py`
   - `engine/api/render_snapshot.py`
   - `engine/api/window.py`
2. Extend `engine/api/game_module.py` with compatibility-safe next-gen methods while preserving current hooks.
3. Add factory entrypoints in `engine/api/*` that instantiate runtime implementations lazily, preserving boundary rules.
4. Add contract tests in `tests/engine/unit/api/` validating:
   - immutability of snapshot dataclasses/views
   - no backend type dependencies exposed by APIs

## Phase 2: Extract Window/Panel Subsystem

1. Create new runtime package for window ownership, e.g. `engine/window/`:
   - backend window adapter (GLFW-backed first)
   - normalized window event translation
   - surface handle creation/provision
2. Move window-mode and OS lifecycle operations out of `engine/rendering/scene_runtime.py`.
3. Update `engine/runtime/bootstrap.py` composition:
   - build window layer first
   - pass surface handle to renderer backend
   - connect normalized events from window layer to input subsystem
4. Update `engine/runtime/pygfx_frontend.py` to remove direct backend ownership assumptions.
5. Add tests:
   - `tests/engine/unit/window/` for resize/DPI/focus/minimize events and surface provisioning
   - integration test proving renderer no longer creates/owns OS window

## Phase 3: Deterministic Input Snapshot Pipeline

1. Evolve input runtime from drain queues to frame snapshots:
   - keep `InputController` only as backend event collector/adapter
   - add frame assembler in `engine/input/` that normalizes and freezes state per frame
2. Introduce immutable snapshot handoff into host frame flow:
   - host obtains one snapshot at frame boundary
   - simulation reads only that snapshot during frame step
3. Replace direct per-event forwarding in `engine/runtime/pygfx_frontend.py` with snapshot submission.
4. Add tests in `tests/engine/unit/input/`:
   - no mid-frame mutation
   - keyboard/mouse/controller/action map presence in snapshot
   - deterministic ordering/contents for equal input sequences

## Phase 4: Action Mapping and Replay Compliance

1. Add/expand action-map runtime under `engine/input/` (can build on `engine/api/commands.py` and `engine/runtime/commands.py` concepts).
2. Move physical-to-logical mapping responsibility out of app-specific UI framework routing paths.
3. Update replay recording in `engine/runtime/host.py`:
   - record logical actions (or action-resolved snapshot stream)
   - stop relying on raw pointer/key/wheel payloads for deterministic replay core
4. Add diagnostics emission for:
   - mapping conflicts
   - event rate counters
   - device connection lifecycle
5. Add replay tests in diagnostics/runtime suites ensuring replay does not require physical device state.

## Phase 5: Simulation/Rendering Decoupling via RenderSnapshot

1. Introduce simulation-first frame orchestration in host:
   - run simulation/update
   - build immutable render snapshot
   - submit snapshot to renderer
2. Refactor Warships module path:
   - split rendering responsibilities currently embedded in update loop in `warships/game/app/engine_game_module.py`
   - keep `warships/game/ui/game_view.py` as a projection builder or renderer adapter that consumes snapshot-ready view data, not live mutation logic
3. Add adapter layer translating `RenderSnapshot` into renderer retained/immediate submissions.
4. Add tests:
   - renderer cannot observe live simulation mutations post-snapshot build
   - snapshot carries final transforms only

## Phase 6: Explicit Renderer Lifecycle and Pass Pipeline

1. Refactor renderer internals (`engine/rendering/scene.py` and helpers) into explicit staged pipeline:
   - `begin_frame`
   - batch build
   - pass execution
   - `present`
   - `end_frame`
2. Preserve retained and immediate entrypoints but route both into common batch construction.
3. Add pass descriptors/types to support:
   - world pass
   - UI/overlay pass
   - optional future post pass
4. Expand render diagnostics events to include per-stage lifecycle boundaries and batch/pass stats.
5. Add unit tests validating phase ordering and pass execution determinism.

## Phase 7: Rendering Policy Hardening

1. Enforce deterministic draw ordering:
   - explicit layer key
   - stable sort fallback rules for equal layers
2. Evolve snapshot/render math model toward dimension-neutral representation:
   - `Vec3` positions with `z=0` default for 2D
   - `Mat4` transform representation for snapshot payloads
3. Enforce color space behavior in backend config and shader/material path:
   - linear-space internal math
   - sRGB-flagged textures where applicable
   - sRGB presentation path
4. Harden resize path:
   - surface reconfigure only
   - projection/viewport update
   - no full renderer/device rebuild
5. Encode one-frame-in-flight default in renderer scheduling path and diagnostics.
6. Add policy guard tests:
   - ordering stability
   - color/presentation expectations
   - no asset I/O calls inside renderer runtime path
   - one frame in flight behavior

## Phase 8: Diagnostics, Thread Readiness, and Cleanup

1. Complete diagnostics schema coverage across subsystems:
   - window events
   - input pipeline and mapping events
   - render lifecycle and pass metrics
2. Add snapshot exchange abstraction supporting future thread split:
   - double-buffered or atomic-swap snapshot container
   - no shared mutable simulation/render state coupling
3. Remove compatibility/legacy paths:
   - raw per-event GameModule hooks (after parity)
   - legacy frontend glue that bypasses snapshots
4. Finalize boundaries and enforce with tests:
   - import boundary checks
   - runtime integration parity tests
   - replay determinism checks

---

## Validation Strategy

1. Add/extend unit tests:
   - `tests/engine/unit/input/`
   - `tests/engine/unit/rendering/`
   - new `tests/engine/unit/window/`
2. Extend integration tests:
   - `tests/engine/integration/`
   - `tests/warships/integration/app_engine/`
3. Extend import-boundary checks to block backend leakage from core API surfaces.
4. Keep migration phases gated by phase exit criteria before advancing.
5. Add explicit policy-guard tests for:
   - one-frame-in-flight baseline
   - no renderer asset I/O
   - snapshot contains final transforms
   - window resize path passes explicit DPI scale and physical pixel dimensions to renderer

## Recommended Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8

## Notes

- Preserve backward compatibility only through the migration window.
- Keep each phase PR-sized and independently testable.
- Prefer additive interfaces first, then deprecate and remove old paths after parity.

---

## Final Non-Audio Policy Closure (2026-02-20)

This section records the final closure pass against:
- `docs/architecture/input_policies.md`
- `docs/architecture/rendering_policies.md`
- `docs/architecture/window_and_panel_policies.md`

### Items Closed In This Pass

1. Removed raw-event compatibility entrypoints from host runtime:
   - deleted `EngineHost.handle_pointer_event(...)`
   - deleted `EngineHost.handle_key_event(...)`
   - deleted `EngineHost.handle_wheel_event(...)`
   - simulation path now accepts only immutable `InputSnapshot` via `handle_input_snapshot(...)`
   - code: `engine/runtime/host.py`

2. Removed canvas-bound input backend path from input subsystem:
   - deleted `InputController.bind(...)`
   - deleted direct canvas event handlers (`_on_pointer_*`, `_on_key_*`, `_on_char`, `_on_wheel`)
   - input ingestion now comes from normalized window-polled events only (`consume_window_input_events(...)`)
   - code: `engine/input/input_controller.py`

3. Enforced explicit window -> renderer resize contract:
   - frontend now forwards normalized `WindowResizeEvent` to renderer
   - renderer now applies resize from explicit logical/physical/DPI payload through `apply_window_resize(...)`
   - code: `engine/runtime/pygfx_frontend.py`, `engine/rendering/scene.py`

4. Updated policy-guard tests to match final contracts:
   - input tests now validate window-event ingestion only (no canvas binding path)
   - host tests now validate snapshot-only input handling
   - debug API fake modules no longer rely on removed raw hooks
   - code: `tests/engine/unit/input/test_input_controller.py`, `tests/engine/unit/runtime/test_host.py`, `tests/engine/unit/api/test_debug_api.py`

### Verification Evidence

1. Static typing:
   - `mypy engine warships` passes.

2. Contract and regression tests:
   - `python -m pytest -q tests/engine/unit/input/test_input_controller.py tests/engine/unit/runtime/test_host.py tests/engine/unit/runtime/test_pygfx_frontend.py tests/engine/unit/api/test_debug_api.py`
   - result: `39 passed`.

3. Rendering/window regressions:
   - `python -m pytest -q tests/engine/unit/rendering/test_scene_graphics.py tests/engine/integration/test_resize_diagnostics_pipeline.py tests/engine/integration/test_diagnostics_disabled_parity.py`
   - result: `25 passed`.

### Policy Status (Non-Audio)

1. Input policy: `Compliant`
2. Rendering policy: `Compliant`
3. Window/panel policy: `Compliant`

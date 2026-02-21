# Engine Refactoring Architecture Plan

Date: 2026-02-21  
Status: Active  
Scope: Refactor `engine` package to remove domain leakage, reduce god modules/classes, fix API design issues, and improve sustainability/performance.

## Problem

Current engine architecture has several structural issues that will become expensive to evolve:

1. God module/class concentration (`engine/rendering/wgpu_renderer.py`, `engine/runtime/host.py`).
2. Duplicated UI runtime logic split across `engine/ui_runtime` and `engine/api/ui_primitives.py`.
3. API/runtime boundary blur and dynamic contracts (`Any`/`getattr` heavy paths).
4. Warships-specific naming and semantics leaking into engine core.
5. Hot-path inefficiencies (rebuilding maps, deep transforms/sanitization, clear-all caches).

## Goals

1. Enforce clear engine layering and stable contracts.
2. Remove game-domain assumptions from engine internals and public API.
3. Break down oversized modules into maintainable components.
4. Reduce duplicated logic and establish single ownership for UI runtime primitives.
5. Improve hot-path performance predictability and cache behavior.

## Non-Goals

1. Full rendering backend rewrite.
2. Visual redesign of game UI.
3. Immediate migration of every call site in one commit.

## Findings Baseline (Evidence)

1. `engine/rendering/wgpu_renderer.py` is 4885 LOC and mixes renderer API, backend lifecycle, batching, text shaping/atlas, diagnostics, and CFFI prewarm/fastpath logic.
2. `engine/runtime/host.py` is 820 LOC and mixes frame orchestration, diagnostics, profiling, replay, crash export, HTTP diagnostics server, overlay composition, and render snapshot pipeline details.
3. `engine/api/ui_primitives.py` duplicates functionality present in `engine/ui_runtime/*` (grid, prompt/modal runtime, keymap, list scroll, interaction routing).
4. Warships-specific artifacts remain in engine: `WARSHIPS_RNG_SEED`, `warships_run_*`, `ui_diag_run_*`, and board-specific token names.
5. `RenderAPI` protocol does not declare `add_style_rect`, but implementations and style helpers rely on it via duck typing.
6. `engine/api/*` factories directly import `engine/runtime/*`, reducing contract/runtime separation.
7. Shortcut routing rebuilds command map per key event in `EngineUIFramework`.

## Criteria Review: Unclean Architecture

### Findings (Condensed, Complete)

1. Critical: bidirectional API/runtime dependency and mixed composition root.
   - `engine/api/*` creates runtime implementations (`action_dispatch`, `commands`, `events`, `flow`, `context`, `hosted_runtime`, `ui_framework`, `interaction_modes`, `module_graph`, `screens`, `logging`).
   - `engine/runtime/*` imports `engine.api.*` contracts broadly.
   - `engine/runtime/diagnostics_http.py` depends on `engine.api.debug`, creating inversion.
2. High: API purity violations (non-contract dependencies in API layer).
   - `engine/api/debug.py` and `engine/api/logging.py` import diagnostics/runtime internals.
3. High: protocol incompleteness causes reflective architecture.
   - `WindowPort` lacks members used by runtime frontend (`canvas`, `consume_resize_telemetry`).
   - `RenderAPI` lacks extension methods used in runtime/style paths (`add_style_rect`, resize-specific behavior).
   - Runtime uses `getattr`/`hasattr` at boundaries (`window_frontend`, `ui_space`, `host`).
4. High: hidden backend contract leaks through opaque surface type.
   - `SurfaceHandle.provider: object | None`, while renderer/window require provider behavior (`get_context("wgpu")`).
5. High: duplicate UI runtime ownership.
   - `engine/api/ui_primitives.py` duplicates grid, prompt/modal routing/state, key mapping, scroll/list helpers, and interaction routing already implemented in `engine/ui_runtime/*`.
6. Medium: concrete coupling and weakly typed context boundaries.
   - `HostedWindowFrontend` depends on concrete `EngineHost` instead of minimal host protocol.
   - `RuntimeContext` is service-locator shaped (`dict[str, object]` with string-key lookup).
7. Medium: cross-layer dependency drift outside intended boundaries.
   - `engine/gameplay/update_loop.py` depends on `engine.runtime.time.FixedStepAccumulator`.
   - `engine/rendering/scene_runtime.py` depends on `engine.window.rendercanvas_glfw`.
   - `engine/ui_runtime/debug_overlay.py` depends on `engine.runtime.metrics`.
8. Medium: barrel export surfaces blur layers.
   - `engine/runtime/__init__.py` re-exports API and runtime symbols together.
   - `engine/api/__init__.py` remains a very large umbrella import surface.
9. Medium: config boundary fragmentation.
   - Env parsing and config shaping spread across `runtime`, `diagnostics`, `rendering`, and `ui-space` modules.

### Architecture Decisions (Confirmed)

1. `engine.api` is contracts/types only; runtime wiring moves to explicit composition modules.
2. `engine.ui_runtime` is canonical runtime-UI owner; `engine.api.ui_primitives` becomes thin contracts/value types + compatibility shims.
3. Protocol hardening is strict; required runtime capabilities must be explicit typed interfaces, not reflective probes.

### Audit Coverage and Outcome

1. Static import audit: 96 modules, 211 internal edges.
2. Rule-hit audit: 12 strict hits (`runtime_barrel_mixed_layer`, `api_purity`, `ui_runtime_runtime_dep`, `gameplay_runtime_dep`, `rendering_window_dep`).
3. Runtime smoke checks: module import smoke, headless hosted-runtime smoke, API factory smoke, debug API smoke all passed.
4. Per-module verdict matrix: 17 `needs_refactor`, 79 `clean_for_criterion`.

### Modules Requiring Refactor (Closure Set)

1. `engine/api/__init__.py`
2. `engine/api/context.py`
3. `engine/api/debug.py`
4. `engine/api/logging.py`
5. `engine/api/render.py`
6. `engine/api/ui_primitives.py`
7. `engine/api/window.py`
8. `engine/gameplay/update_loop.py`
9. `engine/rendering/scene_runtime.py`
10. `engine/rendering/wgpu_renderer.py`
11. `engine/runtime/__init__.py`
12. `engine/runtime/context.py`
13. `engine/runtime/diagnostics_http.py`
14. `engine/runtime/host.py`
15. `engine/runtime/ui_space.py`
16. `engine/runtime/window_frontend.py`
17. `engine/ui_runtime/debug_overlay.py`

### Criterion Backlog (Focused)

1. Move all `engine.api` runtime/diagnostics factories and bindings to composition layer.
2. Introduce typed boundary protocols for diagnostics host, style-capable render, resize-capable renderer/window, and explicit surface provider.
3. Remove boundary reflection where capability is architecturally required.
4. Consolidate UI runtime logic under `engine.ui_runtime`; reduce `engine.api.ui_primitives` to non-duplicated API-facing contracts/shims.
5. Relocate fixed-step utility to neutral layer and remove gameplay->runtime dependency.
6. Move window-backend helpers out of rendering helpers and into window/composition.
7. Replace unbounded service-locator usage with typed context members and constrained extension slots.
8. Split/trim mixed barrel exports (`engine/runtime/__init__.py`, `engine/api/__init__.py`).
9. Centralize env/config parsing responsibilities.

### Closure Pass (Unclean Architecture)

Date: 2026-02-21  
Method: static import-rule audit + runtime smoke checks + per-module verdicting.

#### Static Audit Artifacts

1. Import edge dump: `docs/architecture/audits/engine_import_edges.csv`
   - 211 engine-internal import edges across 96 modules.
2. Rule violation dump: `docs/architecture/audits/unclean_architecture_violations.csv`
   - 12 rule hits under strict unclean-architecture ruleset.
3. Module verdict matrix: `docs/architecture/audits/unclean_architecture_module_verdicts.csv`
   - 96 modules reviewed.
   - 17 modules marked `needs_refactor`.
   - 79 modules marked `clean_for_criterion`.

#### Rule Hits Summary

1. `runtime_barrel_mixed_layer`: 7 hits (`engine/runtime/__init__.py`).
2. `api_purity`: 2 hits (`engine/api/debug.py`, `engine/api/logging.py`).
3. `ui_runtime_runtime_dep`: 1 hit (`engine/ui_runtime/debug_overlay.py`).
4. `gameplay_runtime_dep`: 1 hit (`engine/gameplay/update_loop.py`).
5. `rendering_window_dep`: 1 hit (`engine/rendering/scene_runtime.py`).

#### Runtime Smoke Results

1. Import smoke: all 96 engine modules imported successfully.
2. Headless hosted-runtime smoke: passed (`ENGINE_HEADLESS=1`, minimal dummy module, clean shutdown).
3. API factory smoke: passed (`create_command_map`, `create_event_bus`, `create_flow_machine`, `create_runtime_context`, `create_module_graph`, `create_screen_stack`).
4. Debug API smoke: passed with minimal host object.

#### Final Verdict for Criterion: Unclean Architecture

Criterion status: **confirmed present** (high confidence).

Primary closure-set modules requiring refactor:

1. `engine/api/__init__.py`
2. `engine/api/context.py`
3. `engine/api/debug.py`
4. `engine/api/logging.py`
5. `engine/api/render.py`
6. `engine/api/ui_primitives.py`
7. `engine/api/window.py`
8. `engine/gameplay/update_loop.py`
9. `engine/rendering/scene_runtime.py`
10. `engine/rendering/wgpu_renderer.py`
11. `engine/runtime/__init__.py`
12. `engine/runtime/context.py`
13. `engine/runtime/diagnostics_http.py`
14. `engine/runtime/host.py`
15. `engine/runtime/ui_space.py`
16. `engine/runtime/window_frontend.py`
17. `engine/ui_runtime/debug_overlay.py`

Closure note:
This pass covers all current `engine` modules for this criterion with static and runtime smoke validation. Remaining risk is architectural intent mismatch (intentional transitional coupling), not discovery coverage.

## Criteria Review: Potentially Unsustainable Code or Architecture

### Findings (Condensed, Complete)

1. Critical: complexity concentration in core runtime/renderer.
   - `engine/rendering/wgpu_renderer.py` (4885 LOC, 192 defs; `_WgpuBackend` 68 methods; `draw_packets` 247 lines).
   - `engine/runtime/host.py` (820 LOC; `EngineHost.frame` 162 lines, multi-domain and branch-heavy).
2. High: broad exception swallowing is overused.
   - 80 `except Exception` uses total; concentrated in renderer/window/profiling paths.
3. High: reflective runtime behavior is pervasive.
   - 243 `getattr` uses total; largest concentrations in renderer, debug API, and host runtime.
4. High: third-party/private API patching occurs inside high-traffic modules.
   - Window layer touches private backend internals and patches canvas behavior.
   - Renderer patches `wgpu_native` internals and stores custom patch state.
5. High: duplicated runtime logic creates sustained dual-maintenance burden.
   - Parallel implementations across `engine/api/ui_primitives.py` and `engine/ui_runtime/*` (grid/prompt/modal/interactions/keymap/scroll/list helpers).
6. High: configuration surface is large and fragmented.
   - 83 unique `ENGINE_*`/`WARSHIPS_*` tokens observed; env parsing helpers duplicated across modules.
7. High: import-cycle density is non-trivial.
   - 12 strongly-connected module components, including multi-module runtime/bootstrap/debug cycles and repeated API<->runtime two-node cycles.
8. High: import-boundary tests have a blind spot.
   - API purity test currently checks top-level imports only (`top_level_only=True`), allowing function-scoped coupling drift.
9. Medium: global cache/state strategy is uneven.
   - Multiple global/module caches and clear-all thresholds (notably renderer/ui-space) can create latency cliffs and opaque tuning behavior.
10. Medium: defaults/parsing overlap and drift.
   - Resolution defaults differ by subsystem (`1280x800` vs `1200x720`), with duplicated resolution parsing across bootstrap/ui-space/renderer.
11. Medium: renderer still contains domain-leaning defaults and implicit string protocols.
   - Game-leaning text-prewarm labels in generic renderer path.
   - Large `kind`/`stream_kind` string-dispatch chains in hot paths.
   - Private metadata keys (`_engine_static`, `_engine_version`) act as hidden protocol.
12. Medium: optional dependency behavior is bound at import-time.
   - Optional imports (`numpy`, `uharfbuzz`, `orjson`) define behavior by environment at import moment, reducing reproducibility.
13. Medium: public export surfaces are oversized.
   - `engine/api/__init__.py` exports 144 symbols; `engine/runtime/__init__.py` exports 31.
14. Medium: helper-family proliferation and ownership ambiguity continue.
   - Repeated `_env_*` / `_flag` helpers and overlapping module responsibilities increase drift risk.
15. Medium: direct module-test touch is uneven for wrapper/barrel modules.
   - Indirection-heavy modules have weaker direct references, raising regression risk during wiring refactors.

### Criterion Outcome

Status: **confirmed present** (high confidence).

### Criterion Backlog (Focused)

1. Define and enforce maintainability budgets:
   - max file size,
   - max function length/branch complexity,
   - broad-exception budget with justified allowlist.
2. Split sustainability hotspots first:
   - `engine/rendering/wgpu_renderer.py`,
   - `engine/runtime/host.py`,
   - `engine/window/rendercanvas_glfw.py`,
   - `engine/runtime/profiling.py`.
3. Replace broad exception patterns with typed handling + explicit fallback telemetry.
4. Reduce reflection in required paths by explicit typed extension interfaces and adapters.
5. Isolate third-party/private API patching to a narrow compatibility module with version guards and tests.
6. Consolidate duplicate runtime logic (`engine/api/ui_primitives.py` vs `engine/ui_runtime/*`).
7. Centralize config parsing and publish one canonical engine config catalog.
8. Align default design resolution policy across host/renderer/ui-space.
9. Strengthen architecture tests:
   - enforce API purity for all imports (not only top-level),
   - add checks for broad exceptions and module budget thresholds.
10. Add import-cycle guardrail in CI and target monotonic cycle reduction per phase.
11. Reduce and tier public export surfaces (`engine.api`, `engine.runtime`) with explicit stability levels.
12. Replace import-time env flag capture in runtime-critical modules with runtime-resolved config access or explicit refresh policy.
13. Replace string-dispatch command handling with typed command registry/dispatcher where feasible.
14. Promote private packet metadata keys to explicit typed fields/contracts (or isolate behind adapter boundary).
15. Add targeted tests for currently low-direct-reference wrapper/barrel modules that encode critical wiring behavior.

## Refactoring Principles

1. Contracts first: define target interfaces before moving implementations.
2. One owner per concern: no duplicate runtime logic in parallel modules.
3. Backward compatibility by adapters during migration.
4. Small, testable slices with measurable exit criteria.

## Execution Phases

### Phase 1: Domain Decoupling and Naming Cleanup

Work:
1. Replace Warships-specific env/config names with engine-generic names and provide compatibility aliases.
2. Replace hardcoded Warships log filename patterns with generic runtime prefixes and backward-compatible discovery support.
3. Remove board/game-specific naming from generic style tokens and primitives.
4. Keep compatibility aliases limited to migration window and document removal timeline.

Exit:
1. Engine core contains no game-title-specific identifiers in contracts/config keys.
2. Existing logs/env vars continue to work through compatibility layer.

### Phase 2: API Contract Hardening

Work:
1. Make `engine.api` contracts/types only: remove runtime/diagnostics bindings from API modules and move wiring to composition.
2. Define explicit renderer/window/surface extension contracts (`StyleRenderAPI`, resize-capable renderer/window contracts, typed surface-provider contract replacing opaque `provider: object | None` assumptions).
3. Replace `Any` host debug access with typed diagnostics host protocol.
4. Remove `getattr`/`hasattr` boundary probing where capability is required.
5. Harden boundary tests to detect function-scoped runtime/rendering imports in `engine/api`.

Exit:
1. `engine.api` has no direct runtime/diagnostics imports.
2. Runtime/composition paths rely on explicit typed boundary protocols.
3. Required boundary behavior no longer depends on reflection.
4. API boundary test policy catches both top-level and lazy import violations.

### Phase 3: UI Runtime Consolidation

Work:
1. Consolidate runtime-UI ownership in `engine.ui_runtime` and migrate all runtime consumers there.
2. Remove duplicated implementations from `engine.api.ui_primitives` (grid, prompt/modal state + routing, key mapping, scroll/list helpers, interaction routing).
3. Keep API-facing shims/re-exports only for migration period.
4. Decouple `engine/ui_runtime/debug_overlay.py` from `engine.runtime.metrics` via stable view/protocol.

Exit:
1. One implementation per UI runtime concept.
2. No divergent copies of identical logic across packages.
3. UI runtime package has no runtime-internal coupling that violates layer boundaries.

### Phase 4: EngineHost Decomposition

Work:
1. Extract `EngineHost` concerns into dedicated components:
   - frame orchestration/service loop
   - diagnostics/replay/crash service
   - render snapshot preparation/scaling/sanitization pipeline
   - overlay integration service
2. Keep `EngineHost` as orchestration facade with narrow dependencies.
3. `HostedWindowFrontend` depends on host protocol rather than concrete `EngineHost`.
4. Replace weakly typed context/service-locator usage with typed context surfaces where required.
5. Remove import-time toggle capture in host-critical paths; use explicit runtime config snapshots/refresh policy.
6. Reduce broad exception/fallback blocks in host/neighboring runtime orchestration paths with typed error handling.

Exit:
1. `EngineHost` is coordination-oriented, not feature-heavy.
2. Unit tests target extracted services independently.

### Phase 5: Renderer Module Decomposition

Work:
1. Split `wgpu_renderer.py` into focused modules:
   - public renderer facade
   - packet translation and sort logic
   - backend/device/surface lifecycle
   - text shaping and atlas subsystem
   - diagnostics/profiling hooks
   - native fastpath/prewarm utilities
2. Establish internal interfaces to reduce cross-cutting state mutation.
3. Move window-backend loop/startup helpers out of `engine/rendering/scene_runtime.py` to window/composition layer.
4. Remove rendering->window backend coupling from rendering runtime helpers.
5. Isolate wgpu-native CFFI fastpath/patch logic into compatibility adapter module with explicit version guards and rollback switch.
6. Remove game-leaning text-prewarm defaults from generic renderer core; move to configurable profile/preset layer.
7. Replace large string-dispatch command handling (`kind`/`stream_kind`) with typed/registered dispatch.
8. Replace private packet metadata key protocol (`_engine_static`, `_engine_version`) with explicit typed contract fields/adapters.
9. Split/contain window-layer private API patching (`rendercanvas` guards) in a dedicated compatibility boundary.

Exit:
1. Renderer subsystem is modular with bounded file size/responsibility.
2. Behavior parity validated via render snapshot/regression tests.

### Phase 6: Performance Hygiene Pass

Work:
1. Replace per-event command-map reconstruction with cached or precompiled shortcut routing.
2. Replace clear-all cache eviction with bounded/LRU strategy where safe.
3. Audit snapshot transform/sanitization path to avoid repeated deep rebuilds when data identity is unchanged.
4. Centralize env/config parsing helpers to reduce duplicated parsing paths and config drift.
5. Split oversized barrel exports and minimize cross-layer import churn (`engine/runtime/__init__.py`, `engine/api/__init__.py`).
6. Set and enforce sustainability budgets (file size, function complexity, broad exception policy) via CI tests.
7. Standardize design-resolution defaults/parsing across host, renderer, and UI-space.
8. Add import-cycle checks and fail on new cycles in engine package.
9. Introduce export-surface budgets and explicit public/internal API tiers.
10. Remove import-time env captures for diagnostics/profiling toggles in favor of explicit config snapshots.
11. Start migration from string-based render command dispatch to typed registry pattern.
12. Define and enforce explicit metadata contract for renderer static/version hints.
13. Add CI checks for broad exception budget, file/function complexity budget, and top import-cycle non-regression.
14. Reduce export-surface bloat with explicit public/internal API tiers and symbol budgets.
15. Add targeted wiring tests for low-direct-reference wrapper/barrel modules.

Exit:
1. Hot-path allocations and latency spikes are reduced and measured.
2. Frame-time p95 does not regress; target improvement in input/render heavy scenarios.
3. Maintainability budget checks pass and prevent regression of core hotspots.
4. Engine import-cycle count trends downward and does not regress.
5. Runtime behavior does not depend on hidden import-time env capture for critical toggles.
6. Sustainability budgets and API/export-surface checks prevent hotspot regression.

## Work Breakdown Priority

1. Phase 1 (domain decoupling)
2. Phase 2 (contract hardening)
3. Phase 3 (UI consolidation)
4. Phase 4 (host decomposition)
5. Phase 5 (renderer decomposition)
6. Phase 6 (performance hygiene)

## Acceptance Criteria

1. No game-specific identifiers remain in engine contracts/config defaults.
2. `engine/api` contracts are typed and do not depend on broad runtime reflection for core features.
3. Duplicate UI runtime logic is removed and replaced by one canonical implementation.
4. `EngineHost` and renderer responsibilities are decomposed into maintainable modules.
5. Input and frame hot paths avoid unnecessary rebuild/eviction behavior and show stable performance.

## Risks and Mitigation

1. Risk: Large refactor breaks behavior across runtime/input/render paths.
   - Mitigation: phase gating, compatibility adapters, and regression tests per phase.
2. Risk: Migration churn for existing imports.
   - Mitigation: temporary shims/re-exports with deprecation markers.
3. Risk: Performance regressions from abstraction splits.
   - Mitigation: baseline measurements before each phase and perf checks in CI.

## Initial Task Queue

1. Create issue set from each phase with explicit file targets and owners.
2. Implement Phase 1 aliases/migrations and add compatibility tests.
3. Draft target protocols for Phase 2 (`DiagnosticsHost`, `StyleRenderAPI` or equivalent).
4. Produce Phase 3 migration map listing all duplicated symbol pairs and selected canonical source.

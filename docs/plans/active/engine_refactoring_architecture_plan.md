# Engine Refactoring Architecture Plan

Date: 2026-02-21  
Status: Active  
Scope: Refactor `engine` package to remove domain leakage, reduce god modules/classes, fix API design issues, and improve sustainability/performance.

## Problem

Current engine architecture has gone through several feature additions. It is necessary to do a refactor audit to catch issues, before they cause serious problems.

## Evaluation criterion

1. Unclean architecture
   - 
2. Potentially unsustainable code or architecture
   - 
3. Engine API design issues (unusable, badly designed, overly verbose while lacking feature)
   -
4. Leaking specific game domain into the engine (non generalizable choices and implementations)
   -
5. God classes and god modules
   -
6. SRP violations, Clean and DRY coding paradigm ignoring code
   -
7. Potentially inefficient designs
   -


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

## Refactoring Plan Execution Phases

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


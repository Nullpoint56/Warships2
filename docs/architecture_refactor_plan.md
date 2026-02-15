# Architecture Refactor Plan

## Goal
Establish a hard boundary between `game` (Warships-specific orchestration/features)
and `engine` (runtime/input/render infrastructure), while keeping behavior stable.

## Architecture Decision
- Lifecycle ownership: **engine-hosted runtime**.
- Composition model: game implements a small engine-facing game module contract; engine host owns main loop, input pump, render cadence, and shutdown.
- Rationale: the project goal is a reusable engine for multiple games. Centralizing runtime ownership in engine provides consistent startup/lifecycle behavior and better long-term reuse.

## Target Dependency Direction
- `warships/game` (`core`, `ai`, `presets`, `ui`, `app`) -> no backend/runtime implementation imports
- `warships/game/app` -> `warships/game/*` + `engine.api`
- `engine/runtime` -> `engine.api`
- `engine/backends/pygfx` (or runtime pygfx modules) -> `engine.api` + third-party libs

## Phases

### Phase A: Contracts and Boundaries
1. Introduce `engine.api` contracts:
   - render API
   - app port API
2. Add Warships app adapter implementing app port against `GameController`.
3. Make runtime framework consume app port, not `GameController` directly.

### Phase B: Runtime Relocation
1. Add `engine.runtime` frontend bootstrap for pygfx.
2. Route frontend factory through `engine.runtime`.
3. Keep existing ui modules as composition/render pieces.

### Phase C: Controller Decomposition
1. Extract feature coordinators from `GameController`:
   - prompt flow
   - new game flow
   - preset manage flow
   - placement flow
   - battle flow
2. Keep `GameController` as a thin orchestrator facade.

### Phase D: View Decomposition
1. Split `GameView` into screen-focused view modules:
   - new game view
   - preset manage view
   - battle view
   - placement view
   - overlay view
2. Keep `GameView` as render dispatcher.

### Phase E: Renderer Decomposition
1. Split `SceneRenderer` internals into:
   - runtime/canvas/window handling
   - viewport/transform logic
   - retained primitive cache/drawer
2. Keep external render API stable.

### Phase F: Engine Boundary Tightening
1. Move engine-owned runtime/render/input modules out of `warships/game/ui` into `engine`:
   - `ui/scene*.py` -> `engine/rendering/*`
   - `ui/input_controller.py` -> `engine/input/*`
2. Keep compatibility shims in `warships/game/ui` for one migration phase to avoid broad breakage.
3. Repoint `engine.runtime` imports to `engine.rendering` and `engine.input` (no `warships/ui` dependency for backend runtime).
4. Keep game-specific presentation modules in app/ui:
   - `ui/game_view.py`, `ui/views/*`, `ui/layout_metrics.py`, `ui/overlays.py`, `ui/board_view.py`
5. Keep game AI outside engine (domain/gameplay layer), but remove direct app/runtime coupling.
6. Follow-up phase: make `engine.api.app_port` type contracts engine-owned (remove direct `app.ui_state` dependency).

### Phase G: Namespace Consolidation (Engine + Game)
1. Consolidate Warships-specific modules under `warships/game/*`:
   - `app` -> `game/app`
   - `core` -> `game/core`
   - `ai` -> `game/ai`
   - `presets` -> `game/presets`
   - `ui` -> `game/ui`
2. Update all imports to `warships.game.*` for game-domain modules.
3. Keep top-level package split as:
   - `engine/` for runtime/technical infrastructure
   - `warships/game` for Warships-specific gameplay/presentation/application logic
4. Remove temporary compatibility shims once all internal imports are migrated.

### Phase H: Engine-Hosted Lifecycle
1. Introduce engine host runtime entry (`EngineHost`) that owns:
   - window/bootstrap
   - input polling
   - frame loop scheduling
   - shutdown semantics
2. Define engine-facing game module contract (minimal):
   - initialize/start
   - handle input events
   - update/tick
   - produce render-facing UI/frame state
   - shutdown
3. Adapt Warships game package to implement this contract (adapter layer only; preserve current gameplay logic/services).
4. Move top-level `main` composition to engine host startup with game module injection.
5. Remove redundant app-owned loop/runtime orchestration once parity is reached.

### Phase H Migration Plan (Detailed)
1. H1: Contracts and host shell (non-breaking)
   - Add `engine.api.game_module` with explicit game-module protocol and host context types.
   - Add `engine.runtime.host.EngineHost` skeleton that can be constructed/configured but does not yet replace current run path.
   - Exit criteria: code compiles; no behavior changes.
2. H2: Host-driven frame loop parity (keep old path active)
   - Move draw-loop orchestration from `engine.runtime.pygfx_frontend` into `EngineHost`.
   - Keep `PygfxFrontendWindow` as thin compatibility wrapper over `EngineHost`.
   - Exit criteria: runtime behavior unchanged (input, redraw, close), code compiles.
3. H3: Warships game-module adapter
   - Add `warships.game.app.engine_game_module` implementing `GameModule` by delegating to existing controller/view/services.
   - Keep current `GameController` and service graph intact; adapter-only integration.
   - Exit criteria: full game flow works via module adapter path.
4. H4: Composition-root switch
   - Update `warships/main.py` to instantiate `EngineHost` + `WarshipsGameModule`.
   - Keep temporary fallback path behind a feature flag/env var for one transition cycle.
   - Exit criteria: default startup uses engine-hosted path.
5. H5: Decommission legacy loop ownership
   - Remove `warships.game.app.loop.AppLoop` runtime ownership (retain only helper/bootstrap logic if needed).
   - Remove obsolete frontend indirection that duplicates host responsibilities.
   - Exit criteria: single lifecycle owner is `EngineHost`.
6. H6: Cleanup and stabilization
   - Remove transitional compatibility code and dead adapters.
   - Update docs and architecture decision records.
   - Exit criteria: no dual-path runtime logic remains.

### Phase H Risk Controls
- Keep incremental non-breaking steps until H4 switch-over.
- Use explicit feature flag for one-cycle fallback during H4.
- After each Hx step: run compile checks and smoke test (startup, menu input, wheel scroll, resize, prompt modal, shutdown).

## Progress Notes
- Phase F step 1 completed: rendering/input runtime modules moved under `engine` with `warships/ui` compatibility shims.
- Phase F step 2 completed: key normalization and modal runtime core moved to `engine/ui_runtime` with framework shim compatibility.
- Phase F step 6 completed: `engine.api.app_port` no longer imports app/core model types (`AppUIState`, `Coord`); board click uses primitive row/col values.
- Phase F follow-up completed: engine runtime no longer depends on `warships.game.ui.board_view`; `BoardLayout`/`Rect` are now engine-owned in `engine/ui_runtime/board_layout.py` with `warships.game.ui.board_view.py` shimmed.
- Phase F follow-up completed: in-repo imports now reference `engine.ui_runtime.board_layout` directly (shims remain only for external/backward compatibility).
- Phase G step 1 completed: Warships-specific modules moved under `warships/game/*`.
- Phase G step 2 completed: imports rewritten from `warships.(app|core|ai|presets|ui).*` to `warships.game.*`.
- Phase G step 4 completed: compatibility shim modules removed after migration.
- Phase G follow-up completed: engine package was moved out of `warships/` to top-level `engine/` (monorepo split: `engine` + `warships/game`).
- Architecture decision recorded: engine-hosted lifecycle selected as the target model for multi-game engine reuse.
- Phase H step H1 completed: added `engine.api.game_module` contract and `engine.runtime.host.EngineHost` lifecycle shell (non-breaking, no startup-path switch yet).
- Phase H step H2 completed: frame-loop orchestration in `engine.runtime.pygfx_frontend` now runs through `EngineHost` via a temporary module adapter; `PygfxFrontendWindow` remains compatibility wrapper.
- Phase H step H3 completed: temporary frontend-local module adapter extracted to `warships.game.app.engine_game_module.WarshipsGameModule`; `engine.runtime.pygfx_frontend` now only wires engine runtime services + game module.
- Phase H step H4 completed: `warships/main.py` now starts engine-hosted runtime directly via `warships.game.app.engine_hosted_runtime.run_engine_hosted_app`.
- Phase H step H5 completed: app-owned lifecycle ownership and frontend factory indirection were removed from active runtime path.
- Phase H step H6 completed: transitional fallback/compatibility modules removed (`warships.game.app.legacy_runtime`, `warships.game.app.loop`, `warships.game.app.frontend`, `warships.game.app.frontend_factory`) and `engine.runtime.pygfx_frontend` no longer depends on Warships app/controller types.

## Architecture Audit
- Moved to docs/architecture_audit.md (findings + code-based reality check).


# Architecture Refactor Plan

## Goal
Establish a hard boundary between `game` (Warships-specific orchestration/features)
and `engine` (runtime/input/render infrastructure), while keeping behavior stable.

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

# Architecture Refactor Plan

## Goal
Establish a hard boundary between `app` (Warships-specific orchestration/features)
and `engine` (runtime/input/render infrastructure), while keeping behavior stable.

## Target Dependency Direction
- `warships/domain` (`core`, `ai`) -> no runtime/backend imports
- `warships/app` -> `domain` + `engine.api`
- `warships/engine/runtime` -> `engine.api`
- `warships/engine/backends/pygfx` (or runtime pygfx modules) -> `engine.api` + third-party libs

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


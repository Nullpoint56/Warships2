## Architecture Audit (2026-02-15)
### Code Reality Check (Not Based on Execution Notes)
- Slice A (`engine boundary + geometry primitives`): In place.
  - `engine/ui_runtime/geometry.py` exists with engine-local geometry types.
  - `engine/ui_runtime/board_layout.py` no longer imports `warships.*`.
  - Engine-side board hit-testing uses engine-local coordinate type (`CellCoord`).
- Slice B (`generic scroll semantics to engine`): In place.
  - `engine/ui_runtime/scroll.py` exists and provides `apply_wheel_scroll(...)`.
  - `warships/game/app/services/menu_scroll.py` is removed.
  - Controller wheel handlers call engine scroll helper (`warships/game/app/controller.py`).
- Slice C (`duplicate framework cleanup`): In place.
  - `warships/game/ui/framework/interactions.py` removed.
  - `warships/game/ui/framework/key_routing.py` removed.
  - `warships/game/ui/framework/__init__.py` remains as thin compatibility re-export + game widget builders.
- Slice D (`runtime bootstrap ownership tightening`): In place.
  - `engine/runtime/bootstrap.py` exists with `run_pygfx_hosted_runtime(...)`.
  - `warships/game/app/engine_hosted_runtime.py` delegates runtime bootstrap to engine.
  - `engine/runtime/__init__.py` exports `run_pygfx_hosted_runtime`.

### Round 1: General Architectural Issues
1. Boundary leak (high): `engine/ui_runtime/board_layout.py` imports Warships domain types (`warships.game.core.models`).
   - Impact: engine package is not game-agnostic and cannot be reused cleanly.
   - Action: make `BoardLayout` engine-local only (primitive row/col or engine-owned coordinate type + engine-owned board size config).
2. Runtime composition still lives mostly in game package (medium): `warships/game/app/engine_hosted_runtime.py`.
   - Impact: lifecycle owner is engine, but bootstrap composition is still game-centric.
   - Action: introduce `engine.runtime.bootstrap` (engine creates renderer/input/window/host loop), game injects only `GameModule` + config.
3. Duplicate interaction/runtime logic layers (medium): engine has `engine/ui_runtime/interactions.py`, while game still contains overlapping framework modules (`warships/game/ui/framework/interactions.py`, `warships/game/ui/framework/key_routing.py`).
   - Impact: drift risk and unclear ownership.
   - Action: keep one owner (engine runtime helpers); remove or repurpose duplicate game framework modules.
4. Dead-ish host redraw state (low-medium): `EngineHost.redraw_requested()` is set/cleared but not consumed by runtime path.
   - Impact: unnecessary state and confusing API surface.
   - Action: either wire it into scheduling, or remove it.
5. Large orchestration hotspot (low-medium): `warships/game/app/controller.py` remains large.
   - Impact: high change surface and coupling between input, transitions, and state projection.
   - Action: split state projection and input dispatch into dedicated collaborators.
6. Tests out of date with namespace refactor (low): tests still import legacy module paths.
   - Impact: no active regression protection for refactors.
   - Action: migrate tests to `warships.game.*` / `engine.*` imports when test work resumes.

### Round 2: Engine-Extraction Opportunities (Game Code That Likely Belongs in Engine)
1. Scroll semantics utility can move to engine (high candidate):
   - Current: `warships/game/app/services/menu_scroll.py`.
   - Why engine-worthy: purely generic wheel-delta -> list-scroll behavior, no Warships domain dependency.
   - Suggested target: `engine/ui_runtime/scroll.py`.
2. Geometry primitives are misplaced (high candidate):
   - Current: `Rect` lives in `engine/ui_runtime/board_layout.py` while `BoardLayout` currently depends on Warships model types.
   - Why engine-worthy: `Rect` is a foundational engine UI/runtime primitive independent of any game.
   - Suggested target: `engine/ui_runtime/geometry.py` (with `Rect`; optionally `Point`).
3. Base hit-target/button primitive can be engine-owned (medium candidate):
   - Current: `warships/game/ui/overlays.py` defines `Button` dataclass with generic hit-test behavior.
   - Why engine-worthy: generic UI interaction primitive; currently reused via protocol-like usage (`ButtonView`).
   - Suggested target: `engine/ui_runtime/widgets.py` (base `HitRect` / `UIButtonModel`), while Warships keeps label mappings and screen-specific button composition.
4. Modal widget scaffolding split is incomplete (medium candidate):
   - Current: modal input routing is engine-owned, but modal widget model/build/render remain in game (`warships/game/ui/framework/widgets.py`).
   - Why partially engine-worthy: route/state contract is engine-level; model shape is already generic.
   - Suggested target:
     - engine: keep a generic modal widget contract/model and optional default renderer;
     - game: keep theme/colors/text phrasing/layout constants.
5. Remaining game framework package should be pruned or re-scoped (medium candidate):
   - Current: `warships/game/ui/framework/*` still contains modules that overlap with engine runtime helpers.
   - Why: ownership boundary is currently ambiguous.
   - Action: remove duplicated modules; keep only game-specific view-model builders if needed.

### Suggested Execution Order for Next Refactor Cycle
1. Fix engine boundary leak in `board_layout` (remove Warships imports from `engine`).
2. Extract `Rect` into engine geometry module and rewire imports.
3. Move `menu_scroll` into `engine/ui_runtime`.
4. Consolidate/remove duplicated game framework routing modules.
5. Optional: move base button/hit-target model into engine widgets primitives.

### Execution Plan (Active)
1. Slice A: Engine boundary + geometry primitives
   - Create engine-local geometry primitives module.
   - Remove `engine -> warships` import from `engine.ui_runtime.board_layout`.
   - Use engine-local cell coordinate type in board hit-testing.
2. Slice B: Generic scroll semantics to engine
   - Move wheel/list-scroll semantics from game service into engine ui_runtime.
   - Rewire controller to engine helper.
3. Slice C: Duplicate framework cleanup
   - Remove or demote game-side duplicated routing helpers that overlap engine ownership.
   - Keep only game-specific widget/view-model builders.
4. Slice D: Runtime bootstrap ownership tightening
   - Introduce an engine bootstrap entrypoint to reduce game-side runtime composition plumbing.

### Execution Status
- Completed: Slice A
  - Added `engine/ui_runtime/geometry.py` (`Rect`, `CellCoord`).
  - Refactored `engine/ui_runtime/board_layout.py` to engine-local types and removed all `warships` imports.
  - Kept game-domain `Coord` conversion inside game service boundary (`warships/game/app/services/placement_editor.py`).
- Completed: Slice B
  - Added `engine/ui_runtime/scroll.py` with generic wheel/list scroll semantics.
  - Rewired controller to use engine helper (`warships/game/app/controller.py`).
  - Removed game-local duplicate (`warships/game/app/services/menu_scroll.py`).
- Completed: Slice C (routing duplicate cleanup)
  - Removed unused duplicate routing modules:
    - `warships/game/ui/framework/interactions.py`
    - `warships/game/ui/framework/key_routing.py`
  - Simplified `warships/game/ui/framework/__init__.py` into a thin compatibility re-export over engine-owned routing helpers plus game-specific widget builders.
- Completed: Slice D (runtime bootstrap ownership tightening)
  - Added engine bootstrap entrypoint: `engine/runtime/bootstrap.py` (`run_pygfx_hosted_runtime`).
  - Simplified game runtime composition to game-specific module wiring only:
    - `warships/game/app/engine_hosted_runtime.py`.
  - Engine now owns renderer/input/window/host bootstrap plumbing.
- Completed: Post-cycle runtime cleanup
  - Removed unused redraw request state/API from host path:
    - `engine/api/game_module.py`
    - `engine/runtime/host.py`
    - `engine/runtime/pygfx_frontend.py`
  - Extracted key-shortcut policy from adapter into dedicated game policy module:
    - `warships/game/app/shortcut_policy.py`
    - `warships/game/app/engine_adapter.py`
- Completed: Engine widget primitive extraction
  - Moved generic button hit-target primitive into engine:
    - `engine/ui_runtime/widgets.py` (`Button`)
  - Rewired app/ui state and button projection typing to engine-owned primitive.
  - Kept Warships-specific layout/label composition in `warships/game/ui/overlays.py`.
- Completed: Controller decomposition (projection + button composition slice)
  - Extracted UI snapshot projection into dedicated service:
    - `warships/game/app/services/state_projection.py`
  - Extracted aggregate button composition into service:
    - `warships/game/app/services/ui_buttons.py` (`compose_buttons`)
  - Simplified `GameController` by delegating state projection and button assembly.
- Completed: Controller decomposition (button input dispatch slice)
  - Extracted button routing dispatch logic into dedicated service:
    - `warships/game/app/services/input_dispatch.py` (`ButtonDispatcher`)
  - Simplified `GameController.handle_button` to delegate direct/prefixed dispatch behavior.
- Completed: Controller decomposition (pointer/key/wheel policy slice)
  - Extracted pointer/key/wheel precondition and region-target policy:
    - `warships/game/app/services/input_policy.py`
  - Simplified `GameController` input handlers by delegating policy checks:
    - `handle_pointer_move`
    - `handle_pointer_release`
    - `handle_pointer_down`
    - `handle_key_pressed` (placement branch gate)
    - `handle_wheel`
- Completed: Controller decomposition (outcome-application consolidation)
  - Consolidated repeated controller mutation patterns into dedicated apply helpers:
    - placement outcomes
    - prompt interaction outcomes
    - prompt confirmation outcomes
  - Reduced duplication across `handle_pointer_*`, `handle_key_pressed`, and prompt handlers.
- Completed: Controller decomposition (setup orchestration slice)
  - Extracted preset refresh/new-game default-selection orchestration:
    - `warships/game/app/services/setup_orchestration.py`
  - Rewired controller methods:
    - `_refresh_preset_rows`
    - `_enter_new_game_setup`
    - `_select_new_game_preset`
    - `_on_new_game_randomize` (shared selection-state applier)
- Completed: Controller decomposition (transition orchestration slice)
  - Extracted transition flag execution helper:
    - `warships/game/app/services/transition_orchestration.py`
  - Rewired `GameController._apply_transition` to delegate side-effect orchestration via callbacks.
- Completed: Controller decomposition (prompt orchestration slice)
  - Extracted prompt interaction/confirmation outcome orchestration:
    - `warships/game/app/services/prompt_orchestration.py`
  - Rewired prompt handlers in `GameController` to delegate outcome application and side effects.
- Completed: Controller decomposition (mutation orchestration batch)
  - Extracted remaining mutation-heavy outcome application into:
    - `warships/game/app/services/mutation_orchestration.py`
      - placement outcome application
      - battle turn outcome application
      - edit-preset result application
  - Rewired `GameController` event handlers (`handle_board_click`, placement handlers, `_edit_preset`) to delegate these mutations.
- Completed: Controller decomposition (state container introduction)
  - Introduced unified mutable controller state model:
    - `warships/game/app/controller_state.py` (`ControllerState`)
  - Migrated `GameController` field reads/writes to `self._state_data.*`.
  - Controller now acts more explicitly as orchestrator over a single state container + extracted services.
- Completed: Controller decomposition (state-driven orchestration simplification)
  - Updated orchestration services to mutate `ControllerState` directly (reduced callback/lambda wiring):
    - `warships/game/app/services/transition_orchestration.py`
    - `warships/game/app/services/prompt_orchestration.py`
    - `warships/game/app/services/mutation_orchestration.py`
  - Simplified `GameController` integration points to pass shared state + minimal side-effect callbacks.


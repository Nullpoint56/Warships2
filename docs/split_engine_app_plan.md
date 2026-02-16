# Split Engine-App Plan

Date: 2026-02-15
Scope: finish full Engine <-> App separation for current Warships codebase

## Objective

Complete boundary hardening so:
- `engine/` contains reusable runtime/render/input/ui-runtime mechanisms
- `warships/game/` contains only Warships domain, game policy, and presentation
- integration happens only through explicit engine contracts/adapters

This document intentionally excludes broader engine generalization work (tracked separately in `docs/engine_generalization_plan.md`).

## Boundary Rules

1. `engine/*` must never import `warships.*`.
2. Engine-app integration must go through:
- `engine/api/game_module.py`
- `engine/api/app_port.py`
- `engine/api/render.py`
3. Game may depend on engine mechanisms, but engine must not depend on game policy/state/domain.
4. Warships-specific states/rules/AI/preset semantics stay in `warships/game/*`.

## Current Status

Already in place:
- Engine-hosted lifecycle path is active (`engine/runtime/*`, `warships/game/app/engine_hosted_runtime.py`).
- Engine UI runtime handles core input routing (`engine/ui_runtime/*`, `engine/runtime/framework_engine.py`).
- Engine boundary is clean (no `engine -> warships` imports).

Remaining split work:
- remove remaining generic helpers from game package where they are not domain-specific
- reduce app/controller orchestration coupling to engine-neutral helpers

## Final Candidate Validation (Game-Agnostic + Dimension-Agnostic)

Validated engine-migration candidates:
1. `warships/game/app/services/input_dispatch.py`
- Reason: pure action-id dispatch utility, no Warships or rendering assumptions.

2. Generic list viewport helpers currently in:
- `warships/game/app/services/state_projection.py` (`visible_rows`, `can_scroll_down`)
- `warships/game/app/services/preset_flow.py` (slice/clamp helpers)
- Reason: generic list-window math; reusable in UI flows regardless of game domain.

3. Generic prompt interaction mechanics in `warships/game/app/services/prompt_flow.py` (partial only):
- open/close state
- key/button/char transitions
- Reason: generic input-state mechanism.
- Keep in game: preset save/rename/overwrite confirm policy.

Rejected for this split phase (would add game or 2D coupling):
1. `warships/game/app/services/input_policy.py::resolve_wheel_target`
- Coupled to Warships screen rectangles (`NEW_GAME_SETUP`, `PRESET_PANEL`).

2. `warships/game/ui/framework/widgets.py`
- Contains concrete modal rendering composition and Warships layout metrics.

3. `warships/game/app/events.py`
- Contains Warships board-specific event DTO (`BoardCellPressed` with domain coord).

4. `warships/game/app/shortcut_policy.py`
- Mapping is game UX policy, not engine mechanism.

## Execution Plan

## Progress

- Slice A: Done
- Slice B: Done
- Slice C: Done
- Slice D: Done
- Slice E: Done

### Slice A: Move generic dispatch helper to engine

- Move:
  - `warships/game/app/services/input_dispatch.py` -> `engine/runtime/action_dispatch.py`
- Rewire imports in game app services/controller.
- Keep behavior identical.
- Status: Done

### Slice B: Move generic list viewport helpers to engine

- Create `engine/ui_runtime/list_viewport.py` with generic helpers:
  - visible slice
  - can-scroll-down
  - clamp scroll
- Replace game-local generic list helpers in:
  - `warships/game/app/services/state_projection.py`
  - `warships/game/app/services/preset_flow.py`
- Keep Warships preset/domain operations in game.
- Status: Done

### Slice C: Move generic prompt interaction runtime to engine (partial)

- Extract generic prompt input state machine from:
  - `warships/game/app/services/prompt_flow.py`
- New engine module:
  - `engine/ui_runtime/prompt_runtime.py`
- Keep game-specific confirm behavior (save/rename/overwrite preset) in game prompt service.
- Status: Done

### Slice D: Controller boundary cleanup

- Continue reducing `warships/game/app/controller.py` to orchestration facade.
- Move non-domain orchestration helpers behind explicit collaborators.
- Keep domain transitions and game policy in game.
- Status: Done
- Implemented in this slice:
  - Extracted non-domain helper operations into `warships/game/app/services/controller_support.py`.
  - Delegated controller utility methods (`reset_editor`, button projection refresh, preset-manage scroll check, status set, state announcement, loaded-placement apply, new-game selection apply) to the collaborator.
  - Kept domain/game policy transitions in `GameController`.

### Slice E: Exit-Criteria Boundary Hardening (Required)

- Goal: satisfy strict exit criteria around app-engine touchpoints.
- Introduce app-local runtime ports/wrappers under `warships/game/app/ports/` for engine mechanisms currently imported directly in app layer.
- Rewire `warships/game/app/*` modules to depend on app-local ports instead of importing engine mechanism modules directly.
- Keep engine contracts/adapters as canonical integration boundary.

Planned concrete tasks:
1. Add app-local runtime ports module(s), e.g.:
- `warships/game/app/ports/runtime_primitives.py`
- `warships/game/app/ports/runtime_services.py`

2. Move app-layer direct imports behind ports:
- `engine.runtime.action_dispatch`
- `engine.ui_runtime.scroll`
- `engine.ui_runtime.board_layout`
- `engine.ui_runtime.prompt_runtime`
- `engine.ui_runtime.widgets`

3. Scope rule:
- Strict boundary applies to `warships/game/app/*`.
- `warships/game/ui/*` may continue using rendering/runtime contracts where appropriate (presentation layer integration).

4. Update docs and verify:
- Ensure no direct `engine.*` imports remain in `warships/game/app/*` except contracts/adapters by policy.
- Status: Done
- Implemented in this slice:
  - Added app-local ports:
    - `warships/game/app/ports/runtime_primitives.py`
    - `warships/game/app/ports/runtime_services.py`
  - Rewired `warships/game/app/controller.py`, `warships/game/app/controller_state.py`, `warships/game/app/ui_state.py`, and app service modules to import runtime mechanisms via app-local ports.
  - Verified remaining direct `engine.*` imports in `warships/game/app/*` are limited to:
    - engine contracts/adapters (`engine_adapter.py`, `engine_game_module.py`, `engine_hosted_runtime.py`)
    - app-local ports (`warships/game/app/ports/*`)

### Deferred (Not in this split-only branch)

- Wheel target abstraction based on game-defined UI regions.
- Menu/state framework primitives and generalized engine gameplay/AI components.
- These are tracked under `docs/engine_generalization_plan.md`.

## Explicit Keep-in-Game List

These are intentionally not engine migration targets:
- `warships/game/core/*`
- `warships/game/ai/*`
- `warships/game/presets/*`
- Warships state machine and transition policy
- Warships UI layout/content/look-and-feel

## Done Criteria

1. No `engine -> warships` imports.
2. Generic mechanism helpers no longer live under `warships/game/app/services`.
3. `warships/game/app/*` engine touchpoints are only:
- engine contracts/adapters, or
- app-local runtime ports that wrap engine mechanisms.
4. `warships/game/app/controller.py` is primarily orchestration, not utility sink.
5. Runtime behavior remains unchanged from current user-visible flow.
  - Validation source: manual smoke testing after each modification pass (performed by project owner).

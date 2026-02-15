# Warships Design

## Scope

This document describes the current architecture as implemented in code.
It replaces the old `design_v1.md` target/spec document.

Primary goals in the current codebase:
- Engine-hosted runtime lifecycle
- Pygfx-based rendering through engine-owned rendering/runtime modules
- Game-specific rules, state, AI, and UI composition inside `warships.game`
- Clear engine/app boundary through explicit ports and module contracts

## Repository Layout

Top-level runtime/code packages:
- `engine/`: reusable runtime, rendering, input, and UI runtime helpers
- `warships/`: game application and domain implementation
- `warships/game/`: game-specific app/core/ai/presets/ui/infra modules

High-level map:
- `engine/api/`: contracts (`GameModule`, `EngineAppPort`, `RenderAPI`)
- `engine/runtime/`: host/bootstrap/frontend and UI framework event routing
- `engine/rendering/`: `SceneRenderer` and retained scene primitives
- `engine/input/`: input event collection/normalization
- `engine/ui_runtime/`: layout math, interaction routing, modal/wheel helpers
- `warships/game/app/`: controller, adapter, game module, orchestration services
- `warships/game/core/`: game rules and models
- `warships/game/ai/`: AI strategies
- `warships/game/presets/`: preset persistence/services
- `warships/game/ui/`: game-specific views/widgets/layout metrics
- `warships/game/infra/`: env loading and logging setup

## Runtime Ownership and Startup

Entry point:
- `warships/main.py`

Startup flow:
1. `warships.main.main()` loads env and logging.
2. Calls `warships.game.app.engine_hosted_runtime.run_engine_hosted_app()`.
3. Game composition creates controller and module factory.
4. Engine bootstrap `engine.runtime.bootstrap.run_pygfx_hosted_runtime(...)` creates:
   - `BoardLayout`
   - `SceneRenderer`
   - `EngineHost`
   - `InputController`
   - pygfx window frontend
5. Frontend drives frame loop and input dispatch through engine host/module hooks.

This is engine-hosted runtime: the engine owns loop/host/frontend, while Warships provides a `GameModule`.

## Engine Contracts

### Game module lifecycle contract
- File: `engine/api/game_module.py`
- Main protocol: `GameModule`
- Hooks:
  - `on_start(host)`
  - `on_pointer_event(event)`
  - `on_key_event(event)`
  - `on_wheel_event(event)`
  - `on_frame(context)`
  - `should_close()`
  - `on_shutdown()`

### App port contract (UI/input bridge)
- File: `engine/api/app_port.py`
- Main protocol: `EngineAppPort`
- Exposes:
  - UI snapshot/query (`ui_state`, `modal_widget`, `interaction_plan`)
  - input actions (`on_button`, `on_board_click`, pointer/key/char/wheel handlers)

### Render contract
- File: `engine/api/render.py`
- Main protocol: `RenderAPI`
- Used by game views; engine provides implementation (`SceneRenderer`).

## Warships Engine Integration

### Game module adapter
- File: `warships/game/app/engine_game_module.py`
- `WarshipsGameModule` implements `GameModule` and delegates to:
  - `EngineUIFramework` for input routing
  - `GameController` for state/actions
  - `GameView` for rendering

### App adapter
- File: `warships/game/app/engine_adapter.py`
- `WarshipsAppAdapter` implements `EngineAppPort` over `GameController`.
- Converts app state into engine-consumable interaction/modal view models.

### UI framework routing owner
- File: `engine/runtime/framework_engine.py`
- `EngineUIFramework` routes pointer/key/wheel events.
- Uses:
  - modal helpers from `engine/ui_runtime/modal_runtime.py`
  - key/shortcut routing from `engine/ui_runtime/interactions.py` and `keymap.py`
  - board click hit-testing via `engine/ui_runtime/board_layout.py`

## Rendering Architecture

Render backend role:
- `pygfx` + `wgpu` are the concrete rendering backend.
- Engine wraps backend behavior in `SceneRenderer` (`engine/rendering/scene.py`) implementing `RenderAPI`.

Render style:
- Retained keyed primitives (rect/text/grid), synchronized per frame.
- Window-filling background, design-space coordinate transform, redraw invalidation.

Game drawing:
- `warships/game/ui/game_view.py` composes state-specific views:
  - placement/battle boards
  - setup/preset screens
  - status and modal overlays

## UI Runtime and Geometry

Engine-owned general runtime helpers:
- `engine/ui_runtime/geometry.py`: `Rect`, `CellCoord`
- `engine/ui_runtime/board_layout.py`: board layout and screen-to-cell mapping
- `engine/ui_runtime/scroll.py`: generic wheel/list scroll semantics
- `engine/ui_runtime/interactions.py`: non-modal button/shortcut/wheel routing checks
- `engine/ui_runtime/modal_runtime.py`: modal pointer/key routing state machine
- `engine/ui_runtime/widgets.py`: generic widget primitives (`Button`)

Game-owned UI specifics:
- `warships/game/ui/layout_metrics.py`: Warships-specific coordinates/regions
- `warships/game/ui/views/*`: screen-specific rendering logic
- `warships/game/ui/framework/widgets.py`: game-specific modal widget composition/render helper

## Application Layer (Game)

Controller and services:
- `warships/game/app/controller.py` is the orchestration entrypoint.
- Supporting service decomposition under `warships/game/app/services/` includes:
  - transition/state projection
  - setup/preset/prompt/session flows
  - input policy/dispatch
  - mutation orchestration

State model:
- `warships/game/app/state_machine.py`: app states (`MAIN_MENU`, `NEW_GAME_SETUP`, `PRESET_MANAGE`, `PLACEMENT_EDIT`, `BATTLE`, `RESULT`)
- `warships/game/app/ui_state.py`: immutable view snapshot (`AppUIState`)
- `warships/game/app/controller_state.py`: mutable controller-owned runtime state

## Domain and Data

Game rules/model:
- `warships/game/core/*` (board/fleet/models/rules/shot resolution)

AI:
- `warships/game/ai/*` (hunt/target, probability target, pattern hard)

Presets:
- `warships/game/presets/*` (repository/schema/service)
- Data location: `warships/data/presets/*.json`

## Configuration and Logging

Environment/config:
- `warships/game/infra/config.py`: `.env` loader and path resolution
- `engine/rendering/scene_runtime.py`: window/aspect related runtime env interpretation

Logging:
- `warships/game/infra/logging.py`: JSON/text formatter and root logger setup

Important env flags currently used by startup/runtime:
- `WARSHIPS_WINDOW_MODE`
- `WARSHIPS_UI_ASPECT_MODE`
- `WARSHIPS_DEBUG_INPUT`
- `WARSHIPS_DEBUG_UI`
- `LOG_LEVEL`
- `LOG_FORMAT`

## Boundary Rules (Current)

Rules enforced by current architecture direction:
- Engine modules should not import `warships.*`.
- Game integrates with engine only via engine contracts (`GameModule`, `EngineAppPort`, `RenderAPI`).
- Game UI can use engine `RenderAPI` and engine `ui_runtime` utilities, but game screen composition remains in `warships/game/ui`.
- Runtime lifecycle ownership remains in `engine/runtime`.

## Current Status Summary

Implemented:
- Qt-free runtime path (pygfx engine path)
- Engine-hosted lifecycle bootstrap
- Engine-owned UI routing core (modal, key, wheel, board hit-test)
- Decomposed game application services under `warships/game/app/services`

This document is intentionally code-first and should be updated when module boundaries or ownership change.

# Warships Design

Date: 2026-02-16
Scope: current implemented architecture

## Goals

- Engine-hosted runtime lifecycle
- WGPU rendering backend through engine APIs
- Strict engine/game boundary
- Game-specific rules/policy/UI composition kept in `warships/game`

## Repository Topology

- `engine/`: reusable runtime, rendering, input, and UI-runtime mechanisms
- `warships/game/`: Warships app, domain, AI, presets, and presentation

Key engine packages:
- `engine/api/`: contracts (`GameModule`, `EngineAppPort`, `RenderAPI`)
- `engine/runtime/`: host, bootstrap, frontend window adapter, UI framework routing
- `engine/rendering/`: `WgpuRenderer` backend implementation
- `engine/input/`: pointer/key/wheel event collection
- `engine/ui_runtime/`: geometry, grid hit-testing, modal/key/wheel/list helpers

Key game packages:
- `warships/game/app/`: controller, adapter, engine module composition
- `warships/game/core/`: rules and models
- `warships/game/ai/`: AI strategies
- `warships/game/presets/`: persistence and services
- `warships/game/ui/`: Warships-specific layout, widgets, and views
- `warships/game/infra/`: env + logging setup

## Runtime Ownership

Entry point:
- `warships/main.py`

Startup flow:
1. `warships.main.main()` loads env and logging.
2. `warships.game.app.engine_hosted_runtime.run_engine_hosted_app()` composes game objects.
3. `engine.runtime.bootstrap.run_hosted_runtime(...)` builds runtime:
   - `GridLayout`
   - `WgpuRenderer` (or headless renderer when `ENGINE_HEADLESS=1`)
   - `EngineHost`
   - `InputController`
   - frontend window adapter
4. Engine-owned frame/input loop drives the game module.

Window mode ownership:
- Single owner is `EngineHostConfig.window_mode`.
- Bootstrap applies mode via frontend methods.
- Renderer construction has no startup window-mode side effects.

## Engine Contracts

### `GameModule`
File: `engine/api/game_module.py`

Engine calls:
- `on_start(host)`
- `on_pointer_event(event)`
- `on_key_event(event)`
- `on_wheel_event(event)`
- `on_frame(context)`
- `should_close()`
- `on_shutdown()`

### `EngineAppPort`
File: `engine/api/app_port.py`

Bridge from engine UI routing to app actions:
- state queries: `ui_state`, `modal_widget`, `interaction_plan`
- actions: `on_button`, `on_cell_click`, pointer/key/char/wheel handlers

Interaction contract is engine-neutral:
- `cell_click_surface`
- `wheel_scroll_regions`

### `RenderAPI`
File: `engine/api/render.py`

Game UI renders through this API; current implementation is `WgpuRenderer`.

## Engine UI Runtime

Core reusable primitives:
- `engine/ui_runtime/geometry.py`: `Rect`, `CellCoord`
- `engine/ui_runtime/grid_layout.py`: target-based grid rect/cell hit-testing
- `engine/ui_runtime/interactions.py`: button/shortcut/wheel region routing helpers
- `engine/ui_runtime/modal_runtime.py`: modal key/pointer routing state
- `engine/ui_runtime/scroll.py`: wheel scroll semantics
- `engine/ui_runtime/list_viewport.py`: list viewport math
- `engine/ui_runtime/prompt_runtime.py`: generic prompt state transitions

## Game Integration

Engine adapter layer:
- `warships/game/app/engine_game_module.py`: `GameModule` implementation for Warships
- `warships/game/app/engine_adapter.py`: `EngineAppPort` implementation over `GameController`

Important boundary rule:
- Engine receives generic grid targets.
- Warships adapter maps those targets to game semantics (`is_ai_board` etc.).

## Rendering

Backend:
- `wgpu` via `engine/rendering/wgpu_renderer.py`

Model:
- Retained keyed primitives (`rect`, `text`, `grid`) with per-frame activation
- Input uses `to_design_space(...)` to map window coordinates into logical UI design coordinates

## Configuration

Preferred env files:
1. `.env.engine`
2. `.env.engine.local` (gitignored)
3. `.env.app`
4. `.env.app.local` (gitignored)

Ownership:
- Engine settings (`ENGINE_*`):
  - `ENGINE_HEADLESS` (`1|true|yes|on` enables headless mode)
  - `ENGINE_WINDOW_MODE`
  - `ENGINE_UI_ASPECT_MODE`
  - `ENGINE_LOG_LEVEL`
  - `ENGINE_DEBUG_METRICS`
  - `ENGINE_DEBUG_OVERLAY`
- App settings (`WARSHIPS_*` + app log format):
  - `WARSHIPS_DEBUG_INPUT`
  - `WARSHIPS_DEBUG_UI`
  - `WARSHIPS_LOG_LEVEL`
  - `WARSHIPS_APP_DATA_DIR`
  - `WARSHIPS_LOG_DIR`
  - `LOG_FORMAT`

Default runtime app-data root is `<game_root>/appdata` (logs/presets/saves).  
`WARSHIPS_APP_DATA_DIR` overrides that root.

Logging boundary:
- Engine owns logging pipeline via `engine.api.logging` / `engine.runtime.logging`.
- App applies policy by configuring engine logging API (levels/formats/sinks), not by
  mutating runtime internals directly.

Headless and startup failure behavior:
- If `ENGINE_HEADLESS=1`, runtime is allowed to start without renderer initialization.
- If `ENGINE_HEADLESS` is not enabled and wgpu initialization fails, startup raises a hard
  exception with detailed diagnostics (backend/adapter/surface/platform/stack details).

## Boundary Rules

1. `engine/*` must not import `warships.*`.
2. Game integrates with engine through contracts/adapters.
3. Domain/policy stays in game package.
4. Engine contains mechanism and runtime ownership.

## Current Status

Implemented and active:
- Qt removed from runtime path
- Engine-hosted lifecycle
- Neutral engine app-port interaction semantics
- Neutral engine grid primitives (`GridLayout`)
- Unified window-mode ownership in runtime bootstrap/host config

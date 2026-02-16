# Engine Generalization Plan

Date: 2026-02-16
Scope: post-split branch/PR (separate from completed engine-app split work)

## Goal

Evolve `engine/` into a reusable foundation for multiple games without coupling to Warships domain logic.

## Non-Goals

- Reopening engine-app split work
- Moving Warships rules/content/UX policy into engine
- Large behavior changes in the currently stable runtime path

## Baseline (Already in Place)

- Engine-hosted lifecycle and frame loop
- Engine render API + PyGFX backend
- Engine input collection and UI routing
- Neutral app-port interaction semantics (`grid_click_target`, `wheel_scroll_regions`)
- Neutral grid primitive (`GridLayout`)

## Priority Tracks

### Track A: Runtime Composition Primitives

1. `engine/runtime/screen_stack.py`
- Push/pop/replace layered screens
- Overlay support without game-specific assumptions

2. `engine/runtime/flow.py`
- Generic state graph + transition executor
- Guard/callback hooks and transition context

3. `engine/runtime/interaction_modes.py`
- Mode machine (`default`, `modal`, `captured`, custom)
- Routing gates integrated with existing input path

### Track B: Gameplay Host Primitives

1. `engine/gameplay/system.py`
- Standard system lifecycle protocol

2. `engine/gameplay/update_loop.py`
- Ordered system ticks (fixed/variable step)

3. `engine/gameplay/state_store.py`
- Typed state container + snapshot/update helpers

### Track C: AI Primitives

1. `engine/ai/agent.py`
- `decide(context) -> action` contract

2. `engine/ai/blackboard.py`
- Shared context storage with typed keys/helpers

3. `engine/ai/utility.py`
- Generic scoring/composition helpers

### Track D: Core Engine Services (Missing Today)

1. `engine/runtime/time.py`
- Frame time and delta provider (`TimeContext`)
- Fixed-step accumulator helper for deterministic updates

2. `engine/runtime/scheduler.py`
- Engine-owned deferred/interval task scheduler
- Replaces ad-hoc frame-index timing in game orchestration

3. `engine/assets/registry.py`
- Typed asset handle + registry/load lifecycle hooks
- Keeps renderer/game modules from directly coupling to file loading policy

4. `engine/runtime/commands.py`
- Input-to-command mapping primitives (`Command`, `CommandBinding`, `CommandMap`)
- Decouples game actions from raw key names and wheel/button plumbing

5. `engine/runtime/events.py`
- Lightweight event bus contract for module/system boundaries
- Pub/sub primitives only (no game-domain event types)

### Track E: Module/Subsystem Composition

1. `engine/runtime/module_graph.py`
- Ordered module startup/shutdown/update dependency graph
- Avoids custom lifecycle wiring per game module

2. `engine/runtime/context.py`
- Shared engine context object (render/input/time/scheduler/services)
- Stable injection point for modules/systems without reaching into runtime internals

## Keep in Game

- Warships domain states and transitions
- Fleet/preset/business rules
- Difficulty and AI strategy policy
- Concrete UI layout/look-and-feel
- Game-domain content loading and persistence schema

## Execution Strategy

1. Add engine primitives first with adapters (no behavior change).
2. Adopt incrementally in game orchestration.
3. Remove redundant game-local generic helpers after parity.
4. Validate each slice by manual smoke testing.

## Track Execution Contract (Strict)

We only move to the next track when both are true for the current track:

1. Engine completion gate:
- All items listed in the track are implemented in `engine/`.
- Unit tests for new engine primitives exist and pass.

2. Warships adoption gate:
- Every new engine primitive is evaluated as `applicable` or `not_applicable` for Warships.
- If `applicable`, Warships must use it on a real path (not dead code).
- If `not_applicable`, we must document the reason and the trigger for when it becomes applicable.

Track completion definition (hard requirement):
1. Engine-side implementation is complete.
2. New functionality is available through the `engine.api` layer (no direct game dependency on
   `engine.runtime.*` internals for adopted primitives).
3. Warships is updated to use applicable new functionality through `engine.api`.

API quality rule (mandatory):
1. `engine.api` is not allowed to be only a re-export/proxy layer for new features.
2. For each adopted feature, `engine.api` must define real API surface:
- protocol contracts and/or API dataclasses/enums
- public functions/factories with engine-facing semantics
3. `engine.runtime.*` must implement those API contracts; game code consumes contracts, not runtime internals.
4. Re-export-only stopgaps are allowed only as transitional compatibility shims and must be tracked
   with explicit replacement tasks before track closure.

Current API status:
1. Track A/D adopted primitives now have dedicated API modules:
- `engine.api.commands`
- `engine.api.assets`
- `engine.api.flow`
- `engine.api.screens`
- `engine.api.interaction_modes`
- `engine.api.events`
2. Warships consumes Track A/D applicable primitives through these dedicated API modules.

Recommended slice order:
1. Track D (`time`, `scheduler`, `commands`) as lowest-risk foundational APIs.
2. Track A (`screen_stack`, `flow`, `interaction_modes`) and migrate game menu/state orchestration.
3. Track E (`module_graph`, `context`) to simplify runtime composition.
4. Track B (`system`, `update_loop`, `state_store`) for gameplay loop standardization.
5. Track C (`ai/*`) once gameplay system boundaries are stable.

## Acceptance Criteria

1. No `engine -> warships` imports.
2. New engine APIs stay domain-neutral.
3. A second game could adopt primitives without API redesign.
4. Runtime remains stable while migrating consumers incrementally.
5. Raw input handling can route through engine command mapping without app-specific key plumbing.
6. Frame timing and deferred work are engine-owned primitives (no game-side ad-hoc schedulers).
7. Module lifecycle composition is declarative (graph/context) rather than per-game wiring.

## Implementation Status

- Done:
  - Track A1 `engine/runtime/screen_stack.py` (`ScreenStack`, `ScreenLayer`)
  - Track A2 `engine/runtime/flow.py` (`FlowMachine`, `FlowTransition`, `FlowContext`)
  - Track A3 `engine/runtime/interaction_modes.py` (`InteractionModeMachine`, `InteractionMode`)
  - Track D1 `engine/runtime/time.py` (`TimeContext`, `FrameClock`, `FixedStepAccumulator`)
  - Track D2 `engine/runtime/scheduler.py` (`Scheduler` with one-shot + recurring tasks)
  - Track D3 `engine/assets/registry.py` (`AssetRegistry`, `AssetHandle`)
  - Track D4 `engine/runtime/commands.py` (`CommandMap`, `Command`)
  - Track D5 `engine/runtime/events.py` (`EventBus`, `Subscription`)
  - Host integration:
    - `HostFrameContext` now carries `delta_seconds` and `elapsed_seconds`
    - `EngineHost` advances scheduler each frame and exposes `call_later/call_every/cancel_task`
  - Runtime adoption:
    - Engine shortcut key routing now resolves shortcut actions through `CommandMap`
      in `engine/runtime/framework_engine.py`
  - Engine unit tests added:
    - `tests/engine/unit/runtime/test_screen_stack.py`
    - `tests/engine/unit/runtime/test_flow.py`
    - `tests/engine/unit/runtime/test_interaction_modes.py`
    - `tests/engine/unit/assets/test_registry.py`
    - `tests/engine/unit/runtime/test_commands.py`
    - `tests/engine/unit/runtime/test_events.py`
    - `tests/engine/unit/runtime/test_time.py`
    - `tests/engine/unit/runtime/test_scheduler.py`
- Verified:
  - `uv run mypy`
  - `uv run ruff check .`
  - `uv run pytest tests/engine --cov=engine --cov-fail-under=75`

Track D integration notes:
- `commands` is now on an active game input path (shortcut routing).
- `time`/`scheduler` are integrated at host runtime level and available to game modules.
- `events` is integrated on Warships runtime close lifecycle path.
- `assets` is API-defined and remains not-applicable for current Warships runtime content path.

Track D adoption matrix (for next-gate decision):
1. `time` (`FrameClock`, `TimeContext`): applicable
- Used by host frame loop and passed to Warships module via `HostFrameContext`.

2. `scheduler` (`Scheduler`): applicable
- Integrated into `EngineHost` and available through host control API.
- Used by Warships runtime close lifecycle path via `HostControl.call_later(...)`
  in `warships/game/app/engine_game_module.py`.

3. `commands` (`CommandMap`): applicable
- Used in runtime key shortcut routing on active Warships input path.
- API-defined in `engine.api.commands` and consumed through API constructor.

4. `events` (`EventBus`): applicable
- Used in Warships runtime close lifecycle signaling (`_CloseRequested`)
  in `warships/game/app/engine_game_module.py`.

5. `assets` (`AssetRegistry`): not_applicable_currently
- Warships currently has no runtime-loaded engine-managed assets (textures/audio/fonts).
- Trigger to become applicable: first runtime asset loading path introduced into engine/game runtime.
- API-defined in `engine.api.assets`.

Track D gate decision:
- Engine completion gate: PASS
- Warships adoption gate: PASS (`time`, `scheduler`, `commands`, `events` adopted; `assets` documented
  as not currently applicable with explicit trigger)
- Track D is complete; eligible to proceed to Track A.

Track A adoption matrix:
1. `screen_stack` (`ScreenStack`, `ScreenLayer`): applicable
- Used by `GameController` to track root screen transitions and prompt overlay presence
  in `warships/game/app/controller.py`.

2. `flow` (`FlowMachine`, `FlowTransition`, `FlowContext`): applicable
- Used by `SessionFlowService.resolve(...)` to compute navigation transitions from triggers
  in `warships/game/app/services/session_flow.py`.

3. `interaction_modes` (`InteractionModeMachine`, `InteractionMode`): applicable
- Used by `GameController` input handlers to gate pointer/keyboard/wheel behavior by mode
  (`default`, `modal`, `captured`) in `warships/game/app/controller.py`.

Track A gate decision:
- Engine completion gate: PASS
- Warships adoption gate: PASS
- Track A is complete; eligible to proceed to Track E.

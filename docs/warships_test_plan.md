# Warships Test Plan

Date: 2026-02-16  
Scope: `warships/game/*` only

## Objective

Validate Warships game behavior and policy while keeping engine-independent business logic highly testable.

## Coverage Targets (Aligned with Engine Policy)

1. Global Warships coverage floor: `>= 75%` (`warships/game/*`).
2. Critical pure modules floor: `>= 90%`.
3. Backend-coupled/render-heavy modules are allowed to be lower short-term, but tracked explicitly.

Critical pure module groups for Warships:
1. `warships/game/core/*`
2. `warships/game/presets/*`
3. `warships/game/app/services/*` (excluding orchestration-heavy files if temporarily needed)
4. `warships/game/app/flows/*`

## Status

- Phase W1: Implemented
- Phase W2: Implemented
- Phase W3: Implemented
- Phase W4 (Coverage Hardening): Implemented

Latest measured status (`tests/warships`, February 16, 2026):
1. Global `warships/game/*`: `88%`.
2. Critical pure groups are at/above target:
   - `warships/game/core/*`: `92-95%` by module.
   - `warships/game/presets/*`: `90-96%` by module.
   - stable pure service modules in `warships/game/app/services/*`: mostly `>= 90%`, with key flow modules at `99-100%`.

## Test Strategy

1. Prioritize pure domain and app-service tests.
2. Keep controller tests focused on high-value event flows.
3. Add integration tests at the engine adapter boundary.
4. Avoid GUI backend dependency in default test run.

## Proposed Test Layout

1. `tests/warships/unit/core/`
2. `tests/warships/unit/ai/`
3. `tests/warships/unit/presets/`
4. `tests/warships/unit/app/services/`
5. `tests/warships/unit/app/`
6. `tests/warships/integration/app_engine/`

## Coverage Plan By Module

### Core Domain (`warships/game/core/*`)

#### `models.py`
1. Coordinate and placement model invariants.
2. `cells_for_placement` for horizontal/vertical and bounds assumptions.

#### `board.py`
1. Empty board initialization.
2. `can_place` true/false cases (collision, out-of-bounds).
3. Ship placement id assignment behavior.

#### `fleet.py`
1. `random_fleet` returns complete legal fleet.
2. Deterministic behavior with seeded RNG.

#### `rules.py`
1. Session start initialization.
2. Shot application and turn transitions.
3. Win/lose detection.

#### `shot_resolution.py`
1. Hit/miss/repeat shot handling semantics.
2. Edge coordinates and invalid-shot guards.

### AI (`warships/game/ai/*`)

#### `hunt_target.py`, `probability_target.py`, `pattern_hard.py`
1. Move generation valid/unique.
2. Strategy response to hit/miss history.
3. Deterministic outputs with fixed RNG/board state.

#### `strategy.py`
1. Strategy interface contract compliance.
2. Difficulty-to-strategy selection behavior if applicable.

### Presets (`warships/game/presets/*`)

#### `schema.py`
1. Parse/serialize roundtrip.
2. Invalid schema rejection.

#### `repository.py`
1. Save/load/list/delete with temp directory.
2. Missing file handling.
3. Corrupt JSON failure behavior.

#### `service.py`
1. Name conflicts and overwrite semantics.
2. Integration with repository errors.

### App Services (`warships/game/app/services/*`)

#### `battle.py`
1. Player shot outcome application.
2. AI counterturn trigger.
3. Result-state transitions.

#### `new_game_flow.py`
1. Difficulty selection behavior.
2. Randomize/select preset logic.
3. Preview/source labeling.

#### `placement_editor.py`
1. Reset, list projection, all-ships-placed.
2. `can_place` with temporary board simulation.
3. Palette hit-testing mapping.

#### `placement_flow.py`
1. Left-click pickup from palette/placed ship.
2. Drop success/failure and restore behavior.
3. Rotate/delete held ship logic.
4. Right-click remove/return behavior.

#### `preset_flow.py`
1. Load preset for edit success/failure.
2. Scroll/viewport helpers integration.

#### `prompt_flow.py` and `prompt_orchestration.py`
1. Open/edit/cancel/confirm flows.
2. Rename/save/overwrite policy behavior.
3. Status and pending-save transitions.

#### `session_flow.py` and `transition_orchestration.py`
1. State transitions and side-effect flags.
2. Main menu/new game/manage preset transitions.

#### `setup_orchestration.py`
1. Initial new-game selection resolution.
2. Preset rows/scroll synchronization.

#### `state_projection.py`
1. `AppUIState` projection consistency.
2. Visible list rows and scroll flags.

#### `ui_buttons.py`
1. Button sets per app state.
2. Enabled/disabled toggles in critical states.

#### `input_policy.py`
1. Pointer/key/wheel gating by state.
2. Wheel target resolution with layout metrics.

#### `mutation_orchestration.py`
1. Placement/battle/prompt mutation application correctness.
2. Refresh callback trigger behavior.

#### `controller_support.py`
1. Extracted helper behavior parity with controller expectations.

### App Layer (`warships/game/app/*`)

#### `controller.py`
High-value event-flow tests with fixtures and stubs:
1. Main menu -> new game -> start game transition.
2. Preset manage open/delete/rename entry.
3. Placement edit interactions (pick/rotate/drop/remove).
4. Battle click on enemy grid triggers shot flow.
5. Wheel scrolling affects correct list in correct state.
6. Prompt confirm/cancel paths and status updates.

#### `engine_adapter.py`
1. `interaction_plan` mapping:
   - `grid_click_target`
   - `wheel_scroll_regions`
2. `on_grid_click` maps engine target to `BoardCellPressed.is_ai_board`.
3. Button/key/pointer/wheel forwarders route to controller correctly.

#### `engine_game_module.py`
1. Forwards input events through framework.
2. Frame calls render path and close behavior.
3. Host close when UI requests closing.

#### `ui_state.py`, `controller_state.py`, `state_machine.py`
1. Dataclass defaults and state invariants.
2. Enum/state transition assumptions used by controller/services.

### Infra (`warships/game/infra/*`)

#### `config.py`
1. Env file discovery and loading behavior.

#### `logging.py`
1. Formatter/level setup does not crash on minimal config.

### UI Utility Tests (non-render)

#### `warships/game/ui/layout_metrics.py`
1. Geometry constants and derived rect helpers.

#### `warships/game/ui/overlays.py`
1. Button label mapping and fallback.

#### `warships/game/ui/framework/widgets.py`
1. Modal widget view-model composition (no backend rendering).

## Boundary Integration Tests

### `tests/warships/integration/app_engine/test_adapter_framework_integration.py`

1. Use real `WarshipsAppAdapter` + fake `EngineUIFramework` dependencies.
2. Assert click/key/wheel routing leads to expected controller state changes.
3. Verify grid click semantics stay game-owned at adapter layer.

### `tests/warships/integration/app_engine/test_engine_module_smoke.py`

1. Instantiate `WarshipsGameModule` with fake framework/view/controller.
2. Run `on_start`, `on_frame`, input handlers, `should_close`.
3. Assert lifecycle ordering and close behavior.

## Fixtures

1. `tests/warships/conftest.py`
   - seeded RNG fixture
   - temporary preset repository fixture
   - factory for controller with stubbed preset service
   - sample fleets/sessions
   - fake host/framework/view for module tests

## Execution Phases

### Phase W1 (required baseline)

1. Core domain tests.
2. App service tests for placement/new-game/prompt/session/setup flows.
3. Preset repository/service tests.

### Phase W2

1. Controller high-value flow tests.
2. Engine adapter and module unit tests.
3. Boundary integration tests.

### Phase W3

1. AI behavior tests with deterministic fixtures.
2. Additional infra/UI utility tests.

### Phase W4 (coverage hardening)

1. Raise critical pure groups to `>= 90%`:
   - `warships/game/core/*`
   - `warships/game/presets/*`
   - stable pure service modules in `warships/game/app/services/*`
2. Add branch-completion tests for low modules discovered by coverage report.
3. Keep render/backend-coupled paths out of default strict gate if coverage value is low/noisy.
4. Add CI coverage gates:
   - global `warships/game/* >= 75%`
   - critical pure groups `>= 90%`

## Coverage Commands

Global Warships coverage:
1. `uv run pytest tests/warships --cov=warships.game --cov-report=term-missing`

Critical pure groups (modular runs):
1. `uv run pytest tests/warships/unit/core tests/warships/unit/presets tests/warships/unit/app/services --cov=warships.game.core --cov=warships.game.presets --cov=warships.game.app.services --cov-report=term-missing`

## Definition of Done

1. W1 and W2 green in CI.
2. Main user flows protected by deterministic tests.
3. Adapter boundary behavior covered for future engine generalization work.
4. Coverage gates satisfied:
   - global `warships/game/* >= 75%`
   - critical pure groups `>= 90%`

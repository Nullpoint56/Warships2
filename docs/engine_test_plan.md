# Engine Test Plan

Date: 2026-02-16  
Scope: `engine/*` only

## Objective

Create a stable, fast regression suite for engine mechanisms without relying on Warships domain specifics.

## Status

- Phase E1: Implemented
- Phase E2: Implemented
- Phase E3: Implemented
- Phase E4 (Coverage Hardening): Implemented

## Test Strategy

1. Prefer pure unit tests for deterministic helpers.
2. Use fake ports/renderers for runtime routing tests.
3. Avoid GPU/backend dependency for default test run.
4. Keep slow/integration rendering tests optional/marked.

## Proposed Test Layout

1. `tests/engine/unit/api/`
2. `tests/engine/unit/ui_runtime/`
3. `tests/engine/unit/runtime/`
4. `tests/engine/unit/input/`
5. `tests/engine/unit/rendering/`
6. `tests/engine/integration/runtime/`

## Coverage Plan By Module

### `engine/ui_runtime/geometry.py`

1. `Rect.contains` inclusive/exclusive edge behavior.
2. Negative width/height handling assumptions (document expected behavior).

### `engine/ui_runtime/grid_layout.py`

1. `rect_for_target("primary"|"secondary")` coordinates.
2. Alias target normalization (`player/self/ai/enemy`).
3. Unknown target raises `ValueError`.
4. `screen_to_cell` inside bounds maps correctly.
5. `screen_to_cell` outside bounds returns `None`.
6. Border cell conversion for `(0,0)` and `(size-1,size-1)`.

### `engine/ui_runtime/keymap.py`

1. Common keys mapping (`escape`, arrows, enter/backspace, letters).
2. Unknown keys return `None` or expected passthrough semantics.

### `engine/ui_runtime/interactions.py`

1. `resolve_pointer_button` respects `enabled`.
2. First matching button is selected.
3. `can_scroll_with_wheel` true when any region contains cursor.
4. `route_non_modal_key_event` handles:
   - printable char events
   - key_down mapping
   - shortcut lookup
   - ignored events

### `engine/ui_runtime/list_viewport.py`

1. `visible_slice` clamps and slices correctly.
2. `can_scroll_down` true/false boundaries.
3. `clamp_scroll` for negative and overflow scroll indexes.

### `engine/ui_runtime/scroll.py`

1. Up/down wheel semantics and sign handling.
2. No-op when cannot scroll further.
3. Return contract (`handled`, `next_scroll`) correctness.

### `engine/ui_runtime/modal_runtime.py`

1. Sync from widget view sets focus state correctly.
2. Pointer routing:
   - confirm/cancel button hit
   - input focus capture
   - outside click behavior
3. Key routing:
   - enter/escape/backspace
   - char input path
   - ignored keys

### `engine/ui_runtime/prompt_runtime.py`

1. `open_prompt`, `sync_prompt`, `close_prompt`.
2. Char/key/button transitions.
3. Max-length truncation behavior.
4. Confirm/cancel outcomes and flags.

### `engine/runtime/action_dispatch.py`

1. Direct id dispatch.
2. Prefixed handler dispatch.
3. Unknown action returns expected null/false.

### `engine/runtime/host.py`

1. `start()` idempotency.
2. Frame lifecycle:
   - starts module lazily on first frame
   - increments frame index
   - closes when module requests close
3. Forwarding pointer/key/wheel to module.
4. Shutdown invoked exactly once on close.

### `engine/runtime/framework_engine.py`

Use fake `EngineAppPort`, fake `RenderAPI`, and real `GridLayout`.

1. Pointer routing:
   - modal path precedence
   - button click path
   - cell click path through `cell_click_surface`
   - fallback `on_pointer_down`
2. Key routing:
   - modal key/char path
   - non-modal shortcuts and controller key path
3. Wheel routing:
   - allowed region path
   - blocked path when cursor outside regions

### `engine/runtime/bootstrap.py`

Mock/stub `SceneRenderer`, `InputController`, `create_pygfx_window`.

1. Builds runtime services and wires callbacks.
2. Applies window mode from `EngineHostConfig.window_mode`.
3. Window mode branches:
   - `windowed` -> `show_windowed`
   - `maximized|borderless` -> `show_maximized`
   - `fullscreen` -> `show_fullscreen`
4. Calls `sync_ui` then `run`.

### `engine/runtime/pygfx_frontend.py`

Use fake renderer/input/host.

1. `show_windowed` applies logical size if available.
2. `show_fullscreen` and `show_maximized` invoke runtime mode helper.
3. `_drain_input_events` forwards all queued events.
4. Invalidates renderer when input handling changes UI.
5. Closes renderer when host is closed.

### `engine/input/input_controller.py`

Use fake canvas that captures handler registration.

1. `bind` registers expected event handlers.
2. Pointer down left-button only capture behavior.
3. Pointer move/up, key_down, char, wheel queueing.
4. Drain methods return and clear queues.

### `engine/rendering/scene_viewport.py`

1. `viewport_transform` for preserve-aspect on/off.
2. `to_design_space` offset/scale mapping.
3. Resize extraction helper robustness.

### `engine/rendering/scene_runtime.py`

1. Env resolution helpers (`resolve_preserve_aspect` etc.).
2. Backend loop adaptor selection (`loop.run` vs `run`).
3. Stop helper no-op safety.

### `engine/rendering/scene_retained.py` and `scene_primitives.py`

1. Upsert/hide idempotent behavior with fake node objects.
2. Property-change updates vs no-op update path.

### `engine/rendering/scene.py`

Unit level only by default:
1. Import guards fail with actionable runtime errors when deps missing.
2. Non-graphical helpers that do not require actual backend.

Optional marked integration (`@pytest.mark.graphics`):
1. Construct `SceneRenderer` when deps/backend available.
2. Basic draw-invalidate-close sequence.

## Integration Tests (Engine-only)

### `tests/engine/integration/runtime/test_host_framework_smoke.py`

1. Fake module + fake app port + fake renderer.
2. Simulate pointer/key/wheel/frame sequence.
3. Assert lifecycle and routing order invariants.

## Fixtures and Test Doubles

1. `tests/engine/conftest.py`:
   - fake button/rect/widget models
   - fake app port
   - fake render api with `to_design_space`
   - fake canvas for input controller
   - fake host/module/window for bootstrap/frontend

## Execution Phases

### Phase E1 (required baseline)

1. `ui_runtime/*` pure helpers.
2. `runtime/action_dispatch.py`
3. `runtime/host.py`
4. `runtime/framework_engine.py`
5. `runtime/bootstrap.py`

### Phase E2

1. `input/input_controller.py`
2. `rendering/scene_viewport.py`
3. `rendering/scene_runtime.py`
4. retained/primitives helpers

### Phase E3 (optional/marked)

1. graphics-marked `SceneRenderer` smoke tests.

### Phase E4 (coverage hardening)

1. Raise pure critical modules toward 90%:
   - `engine/ui_runtime/modal_runtime.py`
   - `engine/ui_runtime/prompt_runtime.py`
   - `engine/runtime/framework_engine.py`
2. Raise low-coverage runtime helpers:
   - `engine/runtime/pygfx_frontend.py`
   - `engine/rendering/scene_runtime.py`
   - `engine/rendering/scene_retained.py`
3. Add coverage gates:
   - Engine total >= 75%
   - Critical pure modules >= 90%:
     - `engine/ui_runtime/*`
     - `engine/runtime/action_dispatch.py`
     - `engine/runtime/host.py`

## Definition of Done

1. Baseline phases E1 and E2 green in CI.
2. No backend-required tests in default test lane.
3. Key engine boundary contracts covered by deterministic tests.

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

## Keep in Game

- Warships domain states and transitions
- Fleet/preset/business rules
- Difficulty and AI strategy policy
- Concrete UI layout/look-and-feel

## Execution Strategy

1. Add engine primitives first with adapters (no behavior change).
2. Adopt incrementally in game orchestration.
3. Remove redundant game-local generic helpers after parity.
4. Validate each slice by manual smoke testing.

## Acceptance Criteria

1. No `engine -> warships` imports.
2. New engine APIs stay domain-neutral.
3. A second game could adopt primitives without API redesign.
4. Runtime remains stable while migrating consumers incrementally.

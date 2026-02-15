# Engine Generalization Plan

Date: 2026-02-15
Scope: new branch/PR for building reusable engine-level components and mechanisms

## Goal

Create a generic engine foundation that can support multiple games (2D, 3D, mixed) without engine coupling to Warships domain logic.

This document is intentionally separate from `docs/architecture_improvement_audit.md`.

## Design Constraints

1. Engine must expose mechanism, not game policy.
2. Engine APIs must avoid Warships/domain nouns.
3. New abstractions must be reusable in non-menu, non-2D flows.
4. Game package remains owner of rules/content/state semantics.

## Current Baseline

Engine already provides:
- Runtime lifecycle (`engine/runtime/host.py`, `engine/runtime/bootstrap.py`)
- Input collection/routing (`engine/input/*`, `engine/runtime/framework_engine.py`)
- Rendering API and pygfx backend (`engine/api/render.py`, `engine/rendering/*`)
- UI runtime primitives (modal/key/scroll/layout helpers in `engine/ui_runtime/*`)

Missing generic components:
- Flow/state framework for app/game state transitions
- Screen/layer stack management
- Interaction mode framework beyond current modal handling
- Generic gameplay state/update primitives
- Generic AI primitive contracts/helpers

## Proposed Engine Components

### A) UI Flow and Screen Runtime

1. `engine/runtime/flow.py`
- Generic state graph + transition executor
- Guard hooks and transition callbacks
- Optional transition metadata/context

2. `engine/runtime/screen_stack.py`
- Push/pop/replace screen stack
- Optional overlay layer support
- No assumptions about concrete screen types

3. `engine/ui_runtime/interaction_modes.py`
- Generic mode machine (`default`, `modal`, `captured`, custom)
- Mode-aware input routing gates

4. `engine/runtime/action_map.py`
- Generic action id -> handler mapping utility
- Reusable command/action dispatch helper

### B) Gameplay State Primitives

1. `engine/gameplay/state_store.py`
- Typed state container
- Snapshot/update helpers
- Optional reducer-style update pipeline

2. `engine/gameplay/update_loop.py`
- Ordered system tick execution
- Fixed/variable step support
- Explicit frame context

3. `engine/gameplay/system.py`
- Base protocol for systems/services in update loop
- Lifecycle hooks (`start`, `update`, `shutdown`)

### C) AI Primitives

1. `engine/ai/agent.py`
- Generic `Agent` contract (`decide(context) -> action`)

2. `engine/ai/blackboard.py`
- Shared context bag with typed keys/helpers

3. `engine/ai/utility.py`
- Scoring/composition helpers for utility-based decisions

4. `engine/ai/planner.py` (optional later)
- Lightweight planning interface for goal/action evaluators

## What Stays in Game

- Warships states and transition policy (`MAIN_MENU`, `BATTLE`, etc.)
- Preset/fleet/shot business rules
- AI implementations and difficulty policy
- View/layout aesthetics and text labels

## Migration Strategy

1. Add engine primitives with adapters first (no behavior change).
2. Rewire game orchestration onto engine primitives incrementally.
3. Remove game-local duplicated generic helpers after parity.
4. Keep domain logic in game package throughout migration.

## Proposed Execution Slices

Slice 1: Action dispatch + list/viewport primitives in engine and game rewiring.
Slice 2: Flow runtime + screen stack primitives and migration of session/controller flow wiring.
Slice 3: Interaction mode framework integration with existing modal routing.
Slice 4: Gameplay state/update primitives adoption in game loop/module.
Slice 5: AI primitive contracts adoption and adapter layer for existing Warships AI.

## Acceptance Criteria

1. No `engine -> warships` imports introduced.
2. `warships/game/app/controller.py` orchestration complexity reduced substantially.
3. Engine primitives can be reused by a second sample game without API changes.
4. UI flow runtime is dimension-agnostic (works in 2D and 3D/mixed scenes).
5. AI/gameplay primitives remain generic and do not encode Warships policy.


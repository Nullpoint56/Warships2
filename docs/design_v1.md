# Warships V1 Design

## Scope

V1 is a desktop-only, local single-player Battleship game:
- Player vs AI
- Strict classic Battleship rules
- 2D top-down board
- Click-based turn UI
- No full match save/load
- Ship placement presets can be created, loaded, and saved

## Tech Stack

- Python 3.12+
- `pygfx` for rendering
- `wgpu` backend used by `pygfx`
- `numpy` for board/state operations
- `asyncio` as event loop implementation
- `pytest` for rule and AI tests
- Optional: `pydantic` for preset schema validation

Notes:
- Runtime flow uses standard `asyncio` async/await patterns.
- No `pygame` or similar game engine libraries.

## Core Game Rules (Classic Battleship)

Board and fleet defaults:
- Grid: 10x10
- Ships: Carrier (5), Battleship (4), Cruiser (3), Submarine (3), Destroyer (2)
- Ships cannot overlap
- Ships cannot go out of bounds

Turn sequence:
1. Player fires one shot at AI board
2. Resolve result: miss, hit, sunk
3. If AI still has ships, AI fires one shot at player board
4. Resolve AI result
5. Repeat until one side has all ships sunk

Win conditions:
- Player wins if all AI ship cells are hit
- AI wins if all player ship cells are hit

## High-Level Architecture

Suggested package layout:

```text
warships/
  main.py
  app/
    loop.py
    state_machine.py
  core/
    models.py
    rules.py
    board.py
    fleet.py
    shot_resolution.py
  ai/
    strategy.py
    hunt_target.py
  ui/
    scene.py
    board_view.py
    overlays.py
    input_controller.py
  presets/
    schema.py
    repository.py
    service.py
  infra/
    config.py
    logging.py
tests/
  test_rules.py
  test_board.py
  test_ai_strategy.py
  test_presets.py
docs/
  design_v1.md
```

Layer boundaries:
- `core`: pure game logic, deterministic, no rendering
- `ai`: decision logic over public core state
- `ui`: visualization/input mapping only
- `presets`: loading/saving placement templates
- `app`: game orchestration and state transitions

## Application States

State machine for V1:
- `BOOT`
- `MAIN_MENU`
- `PLACEMENT_EDIT` (place/rotate ships; save preset)
- `PLACEMENT_LOAD` (choose preset)
- `BATTLE`
- `RESULT`
- `EXIT`

Required transitions:
- `MAIN_MENU -> PLACEMENT_EDIT`
- `MAIN_MENU -> PLACEMENT_LOAD`
- `PLACEMENT_LOAD -> PLACEMENT_EDIT` (after loading preset)
- `PLACEMENT_EDIT -> BATTLE` (valid fleet only)
- `BATTLE -> RESULT`
- `RESULT -> MAIN_MENU`

## Domain Model

Use simple dataclasses or typed classes.

Core entities:
- `Coord(row: int, col: int)`
- `Orientation` enum: `HORIZONTAL`, `VERTICAL`
- `ShipType` enum with size mapping
- `ShipPlacement(ship_type, bow: Coord, orientation)`
- `FleetPlacement(list[ShipPlacement])`
- `ShotResult` enum: `MISS`, `HIT`, `SUNK`, `REPEAT`, `INVALID`
- `BoardState`:
  - ship occupancy
  - hit map
  - miss map
  - ship health tracking

Game state:
- `GameState`:
  - player board state
  - AI board state
  - current turn
  - battle history
  - terminal winner (optional)

## Board Representation

`numpy` arrays are recommended:
- `ships: int8[10,10]` (0 = empty, >0 ship id)
- `shots: int8[10,10]` (0 = untouched, 1 = miss, 2 = hit)

Supplemental maps:
- `ship_cells: dict[int, list[Coord]]`
- `ship_remaining: dict[int, int]`

Advantages:
- Fast hit checks and AI candidate filtering
- Straightforward serialization for tests/debug

## AI Design (V1)

Use a deterministic Hunt/Target strategy.

Modes:
- `HUNT`: choose from unshot parity cells (checkerboard) to find ships efficiently
- `TARGET`: once hit is found, prioritize adjacent cells and infer orientation after second hit

AI data needed:
- `unknown_cells`
- `hit_stack` or target queue
- confirmed hit clusters
- orientation hypothesis per cluster

Behavior:
- Never shoot same cell twice
- On `MISS`: continue search
- On `HIT`: move to `TARGET`
- On `SUNK`: clear cluster, return to `HUNT` unless other active cluster exists

Testing focus:
- No repeats across full game simulation
- Sinks all fleet on random seeded boards
- Properly exits `TARGET` on sink

## UI and Rendering (pygfx)

Visual elements:
- Two 10x10 boards (player and AI)
- Grid lines and coordinate labels
- Ship rectangles on player board
- Shot markers (miss dot, hit cross)
- Status text: turn, last action, remaining ships
- Buttons: rotate, randomize, start, load preset, save preset, back/menu

Input:
- Mouse click to place ships and fire shots
- Hover highlight for placement preview
- Rotate via button (optional key shortcut `R`)

Interaction rules:
- In battle, only AI board cells are clickable for firing
- Ignore/feedback on invalid clicks
- Disable input while resolving AI turn animation/timer

## Event Loop and Timing

Startup:
- Use standard `asyncio` loop at app startup
- Run async app loop for UI/events/timers

Tick model:
- Render/update at fixed target (e.g., 60 FPS) or adaptive frame callback
- AI action can be delayed slightly (e.g., 250-500 ms) for readability

Pseudo-flow:

```python
import asyncio

async def main() -> None:
    app = WarshipsApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Preset System (Ship Placement Only)

Preset scope:
- Stores only player fleet placement
- Does not store match progress, shots, turn, or result

Storage location:
- `./data/presets/*.json` (ensure directory exists)

JSON schema (v1):

```json
{
  "version": 1,
  "name": "corner_defense",
  "grid_size": 10,
  "ships": [
    {"type": "CARRIER", "bow": [0, 0], "orientation": "HORIZONTAL"},
    {"type": "BATTLESHIP", "bow": [2, 0], "orientation": "HORIZONTAL"},
    {"type": "CRUISER", "bow": [4, 0], "orientation": "HORIZONTAL"},
    {"type": "SUBMARINE", "bow": [6, 0], "orientation": "HORIZONTAL"},
    {"type": "DESTROYER", "bow": [8, 0], "orientation": "HORIZONTAL"}
  ]
}
```

Validation rules:
- Name non-empty and filesystem-safe
- Exactly one placement per required ship type
- Placements satisfy standard board placement validity
- Reject unknown version

Preset operations:
- `list_presets() -> list[str]`
- `load_preset(name) -> FleetPlacement`
- `save_preset(name, fleet) -> None`
- `delete_preset(name) -> None` (optional for V1)

## Error Handling

- Invalid placement attempt: clear UI feedback; keep state unchanged
- Invalid shot/repeat shot: reject and keep turn
- Corrupt preset file: show non-fatal error and continue
- Missing preset dir: create at startup

## Testing Strategy

Unit tests (`core`):
- Placement validation (bounds, overlap)
- Shot resolution (miss/hit/sunk/repeat)
- Win detection

Unit tests (`ai`):
- No repeated shots
- Target mode adjacency behavior
- Orientation inference and sink handling

Unit tests (`presets`):
- Valid save/load roundtrip
- Rejection of malformed JSON
- Rejection of invalid fleet layouts

Optional integration tests:
- Simulated full games with fixed RNG seed

## Milestones

1. Core rules and domain model
2. Preset repository and validation
3. AI hunt/target strategy
4. Basic `pygfx` board render and click input
5. App state machine and end-to-end playable loop
6. Polish (feedback text, minor animation, tests hardening)

## Open Decisions (Keep for V1.1+)

- Multiple AI difficulty levels
- Placement randomizer sophistication
- Sound effects
- Accessibility options (high contrast, color-blind markers)
- Match analytics/statistics

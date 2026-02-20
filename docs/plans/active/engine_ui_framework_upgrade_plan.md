# Engine UI Framework Upgrade Plan

Date: 2026-02-20  
Status: Draft (parked for later execution)  
Scope: Upgrade engine-level UI framework/layout system so layout behavior is framework-owned, deterministic, and reusable across games.

## Why This Exists

Current UI behavior is partly enforced in game views (Warships-specific fitting/placement rules).  
Target is a framework-first model where layout constraints, overflow, and sizing policies live in engine UI systems.

## Goals

1. Move layout logic from game views into engine UI framework primitives/systems.
2. Enforce parent/child constraint rules and overflow behavior consistently.
3. Keep renderer focused on drawing and final clipping safety, not layout policy.
4. Provide deterministic layout + hit-test behavior that is easy to test.

## Non-Goals

1. No immediate visual redesign work.
2. No immediate migration of every existing view in one pass.
3. No introduction of web-like CSS complexity.

## Common UI Framework Rules to Implement

1. Parent-child constraints (child bounded by parent content box).
2. Intrinsic sizing + min/max clamping.
3. Overflow policies (`clip`, `ellipsis`, `wrap`, optional `scroll`).
4. Box model semantics (margin/border/padding/content).
5. Alignment/distribution rules (start/center/end/stretch + gap).
6. Grow/shrink behavior for container children.
7. Parent auto-size from children (fit-content mode).
8. Deterministic paint/hit-test order.
9. Pixel snapping + DPI-consistent layout mapping.
10. Layout invalidation + minimal recompute.

## Proposed Architecture

1. `engine/ui_runtime/layout/` (new package):
   - `constraints.py`: min/max/intrinsic resolution.
   - `box_model.py`: margin/padding/content math.
   - `containers.py`: stack/flex-like layout containers.
   - `overflow.py`: clip/wrap/ellipsis helpers.
   - `solver.py`: deterministic layout pass.
2. `engine/api/ui_primitives.py`:
   - Keep small primitives and shared utility policies.
   - Expose stable, game-agnostic layout helper API.
3. `engine/api/ui_projection.py`:
   - Project declarative specs through layout constraints.
4. Renderer:
   - Keep final clipping guardrails.
   - No high-level layout decisions.

## Phases

## Phase 1: Layout Foundations

Work:
1. Add core layout data model (`LayoutNode`, `BoxConstraints`, `SizePolicy`).
2. Add deterministic constraint solver for single-level parent-child layout.
3. Add explicit box model calculation helpers.

Exit:
1. Engine unit tests cover constraint resolution and box model behavior.
2. No game code required for this phase.

Visible checkpoint:
1. Standalone layout fixture tests showing consistent parent/child bounds.

## Phase 2: Overflow and Text Policies

Work:
1. Add engine-level overflow modes for text and generic content.
2. Standardize text fitting helpers around framework policies.
3. Add explicit clip regions for children exceeding content box.

Exit:
1. Text never exceeds constrained parent unless policy explicitly allows.
2. Engine tests for clip/ellipsis/wrap behavior.

Visible checkpoint:
1. Long labels in constrained buttons are consistently handled by framework rules.

## Phase 3: Container Layout Systems

Work:
1. Implement stack/flex-like container layout (row/column).
2. Add gap, alignment, and grow/shrink support.
3. Add parent fit-to-children sizing mode.

Exit:
1. Nested container layouts resolve deterministically.
2. Engine tests for row/column layouts and alignment rules.

Visible checkpoint:
1. Main menu layout can be expressed via containers without manual absolute fitting.

## Phase 4: Invalidation and Runtime Integration

Work:
1. Add layout dirty flags and minimal recompute path.
2. Integrate layout pass with current render snapshot flow.
3. Preserve on-demand rendering semantics.

Exit:
1. Layout updates only recompute changed subtrees.
2. No regressions in input hit-testing and render ordering.

Visible checkpoint:
1. Interactive menu updates with stable FPS under resize/input.

## Phase 5: Warships Adoption (Incremental)

Work:
1. Migrate Warships main menu to framework layout nodes.
2. Migrate new-game setup and preset-manage screens.
3. Remove remaining Warships-local layout hacks.

Exit:
1. Warships UI screens use framework layout rules consistently.
2. Manual checks pass for resizing, button labels, hit-testing.

Visible checkpoint:
1. Main menu and setup screens behave correctly without per-screen layout patches.

## Acceptance Criteria

1. No child-overflow regressions on constrained controls.
2. Resizing behavior remains stable and deterministic.
3. Hit-testing matches final rendered layout bounds.
4. FPS remains within acceptable range under normal UI interaction.
5. Layout behavior is validated by engine-level tests, not only game tests.

## Risks and Mitigation

1. Risk: Scope explosion into full UI toolkit.
   - Mitigation: Keep phases small and ship incremental capabilities only.
2. Risk: Regressions in existing absolute-positioned screens.
   - Mitigation: Hybrid support during migration (absolute + container layouts).
3. Risk: Performance regressions in layout recompute.
   - Mitigation: Add dirty-region/dirty-node invalidation before broad adoption.

## Suggested Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5

## Notes

1. This plan intentionally separates engine framework work from Warships content migration.
2. Keep changes policy-first and test-first at engine layer, then adopt in game layer.

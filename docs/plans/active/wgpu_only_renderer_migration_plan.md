# WGPU-Only Renderer Migration Plan

Date: 2026-02-20
Scope: Replace `pygfx` renderer implementation with pure `wgpu`, keep window/input policy boundaries intact, then remove `pygfx` from runtime and dependencies.

## Current State (Fact-Checked)

1. `pygfx` is still required in `pyproject.toml`.
2. Runtime boot path is still pygfx-named and wired:
- `engine/runtime/bootstrap.py` -> `run_pygfx_hosted_runtime(...)`
- `engine/runtime/pygfx_frontend.py` -> `create_pygfx_window(...)`
- `engine/api/hosted_runtime.py` + `engine/api/__init__.py` export `run_pygfx_hosted_runtime`.
3. Renderer is pygfx scene graph based:
- `engine/rendering/scene.py` imports and uses `pygfx`.
4. Window/input architecture is already mostly policy-aligned:
- `engine/window/rendercanvas_glfw.py` emits normalized window/input events.
- `engine/input/input_controller.py` builds immutable `InputSnapshot`.

## Target End State

1. No `pygfx` dependency and no `import pygfx` in active engine/warships runtime paths.
2. Renderer backend is pure `wgpu`, still consumed through `RenderAPI`.
3. Dependency direction remains:
- `WindowLayer -> Surface -> RenderBackend`.
4. Frame contract remains:
- `simulate()` -> `build_render_snapshot()` -> `renderer.render_snapshot(snapshot)`.

## Phase Plan

## Phase 0: Guardrails

### Work
1. Add test guard that fails on `import pygfx` in `engine/` and `warships/` runtime modules.
2. Lock current diagnostics event names used by runtime/render integration tests.
3. Freeze baseline test subset for rendering/window behavior.

### Exit Criteria
1. Guard test active and enforced in CI.
2. Baseline suite green before backend swap.

---

## Phase 1: Introduce New WGPU Renderer Backend

### Work
1. Add `engine/rendering/wgpu_renderer.py` implementing `RenderAPI`.
2. Backend internals are private to rendering package:
- device/surface/pipeline setup
- pass encoder
- snapshot command translator.
3. Keep engine API unchanged:
- no `wgpu` types leaking into `engine/api/*`.

### Exit Criteria
1. New renderer can render empty frame and simple rect/text/grid snapshot path.
2. `RenderSnapshot` contract unchanged.

---

## Phase 2: Surface Attachment and Window Contract Wiring

### Work
1. Wire renderer construction from window-provided surface handle/object only.
2. Update bootstrap composition in `engine/runtime/bootstrap.py`:
- create window layer
- create surface from window layer
- attach renderer to surface.
3. Ensure renderer does not own window lifecycle/event loop.

### Exit Criteria
1. Renderer no longer constructs window/canvas.
2. Runtime composition clearly follows window policy dependency direction.

---

## Phase 3: Port Frame Lifecycle and Pass Pipeline

### Work
1. Keep explicit stage sequence in new renderer:
1. `begin_frame()`
2. build batches
3. execute passes
4. `present()`
5. `end_frame()`
2. Preserve retained + immediate mixed-mode behavior by merging into batch stage.
3. Preserve pass ordering model (`world`, `overlay/ui`, `post_*`).

### Exit Criteria
1. Stage diagnostics emitted and asserted by tests.
2. Deterministic pass execution tests pass.

---

## Phase 4: Resize, DPI, and Surface Reconfigure

### Work
1. Handle normalized `WindowResizeEvent` in renderer with physical size + dpi.
2. Reconfigure surface on resize, update viewport/projection deterministically.
3. Preserve device reuse on resize (no device recreation workaround).

### Exit Criteria
1. Resize diagnostics tests pass.
2. Explicit DPI/logical/physical policy behavior verified in tests.

---

## Phase 5: Rendering Policy Hardening on New Backend

### Work
1. Enforce color policy:
- linear internal math
- sRGB presentation/swapchain.
2. Enforce one-frame-in-flight baseline.
3. Enforce deterministic ordering:
- stable sort by layer + tie-break keys.
4. Ensure renderer performs no asset I/O in runtime path.

### Exit Criteria
1. Policy-guard tests pass for color, ordering, frames-in-flight, and no asset I/O.

---

## Phase 6: Rename Runtime Entry Points to Backend-Neutral Names

### Work
1. Rename frontend module:
- `engine/runtime/pygfx_frontend.py` -> `engine/runtime/window_frontend.py`.
2. Rename bootstrap API:
- `run_pygfx_hosted_runtime(...)` -> `run_hosted_runtime(...)`.
3. Update call sites:
- `engine/api/hosted_runtime.py`
- `engine/api/__init__.py`
- `warships/game/app/engine_hosted_runtime.py`
- tests under `tests/engine/unit/runtime/` and `tests/warships/unit/app/`.

### Exit Criteria
1. No active runtime references to `pygfx_*` names.

---

## Phase 7: Remove Legacy PYGFX Renderer Code

### Work
1. Remove or archive old pygfx renderer modules from active path:
- `engine/rendering/scene.py`
- related pygfx-specific retained helpers if no longer needed.
2. Replace tests tied to pygfx internals with backend-agnostic behavior tests.
3. Remove `pygfx` from runtime metadata collection in `engine/runtime/host.py`.

### Exit Criteria
1. No `import pygfx` in engine runtime path.
2. Rendering tests validate behavior, not pygfx implementation details.

---

## Phase 8: Dependency and Documentation Cleanup

### Work
1. Remove `pygfx` from `pyproject.toml` dependencies and mypy overrides.
2. Update docs referencing pygfx runtime:
- `docs/architecture/system_overview.md`
- operations docs that mention pygfx packaging/runtime.
3. Add a CI guard (grep/import boundary test) blocking reintroduction.

### Exit Criteria
1. `pygfx` absent from dependencies, runtime code, and active docs.
2. Full quality suite green.

## Code Work Map

1. `engine/rendering/`:
- add `wgpu_renderer.py`
- shift public export in `engine/rendering/__init__.py`.
2. `engine/runtime/`:
- update `bootstrap.py` to new renderer and neutral frontend.
- replace `pygfx_frontend.py` with neutral module.
3. `engine/window/`:
- keep ownership of event loop + normalized events + surface provisioning.
4. `engine/api/`:
- rename hosted runtime public entry point.
5. `warships/game/app/`:
- switch to neutral hosted runtime call.
6. `tests/`:
- migrate runtime/rendering tests to new module names and backend-agnostic assertions.

## Policy Compliance Checklist (Must Be Green Before Declaring Done)

1. Rendering policy:
- immutable `RenderSnapshot` consumption only
- explicit frame lifecycle stages
- deterministic ordering
- resize reconfigure without device recreation
- linear internal/sRGB presentation
- one frame in flight
- no renderer asset I/O.

2. Window/panel policy:
- window layer owns loop/lifecycle
- renderer only attaches to provided surface
- normalized resize/dpi events flow window -> renderer
- window diagnostics coverage remains intact.


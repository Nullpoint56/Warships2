# Rendering Policies v1.0

This document defines the non‑negotiable architectural policies governing the engine's rendering subsystem.

The purpose is to prevent hidden coupling, accidental complexity, and large-scale rewrites in future iterations.

---

# 1. Architectural Separation

## 1.1 Simulation–Rendering Decoupling

* Renderer consumes an immutable `RenderSnapshot`.
* Renderer never reads live simulation state.
* Renderer never mutates simulation state.
* Simulation timing is independent of rendering and VSync.

Frame contract:

1. `simulate()`
2. `build_snapshot()`
3. `renderer.render(snapshot)`

---

# 2. Rendering Model

## 2.1 Mixed-Mode Support

Renderer supports:

* Retained mode (persistent objects with identity)
* Immediate mode (stateless per-frame drawing)

Immediate submissions are merged into batching stage.

---

## 2.2 Dimension-Neutral Design

Even in 2D mode:

* Transforms are `Mat4`
* Positions are `Vec3` (z = 0 by default)
* Camera uses view + projection matrices
* Orthographic projection initially

3D capability must be additive, not structural.

---

# 3. Backend Isolation

* `wgpu` or any GPU backend types must not leak into engine API.
* Backend is fully contained inside renderer implementation.
* Simulation and engine core must not manage GPU resources.

---

# 4. Frame Lifecycle

Renderer must implement explicit phases:

1. `begin_frame()`
2. build batches
3. execute passes
4. `present()`
5. `end_frame()`

Renderer must not drive simulation timing.

---

# 5. Resize & Surface Policy

On resize:

* Reconfigure surface
* Recreate depth buffer if needed
* Update projection/viewport

Never:

* Recreate device unnecessarily
* Rebuild entire renderer as workaround

Resize handling must be deterministic and instrumented.

---

# 6. Color Space Policy

* Internal rendering math uses linear color space.
* Textures flagged appropriately (sRGB when applicable).
* Swapchain configured for sRGB presentation.
* Gamma correction occurs at presentation only.

This policy prevents future lighting and post-processing refactors.

---

# 7. Frames in Flight Policy

* One frame in flight (initial implementation).
* No manual GPU fence synchronization unless profiling demands.
* Simplicity prioritized over premature throughput optimization.

---

# 8. Ordering & Transparency

* Deterministic layer-based ordering.
* Stable sort rules.
* Transparency handled via explicit layering.

Depth testing may be introduced later for 3D expansion.

---

# 9. Snapshot Granularity

* Snapshot contains final world transforms.
* Renderer performs no gameplay transform computation.
* Renderer is strictly passive and visual.

---

# 10. Asset Ownership

* Asset loading is separate subsystem.
* Renderer consumes handles or immutable references.
* Renderer does not perform asset IO.

---

# 11. Multi-Pass Capability

Architecture must allow multiple passes per frame.

Even if initial implementation uses a single pass, backend must support:

* World/geometry pass
* Optional overlay/UI pass
* Future post-processing pass

---

# 12. Diagnostics Integration

Renderer must emit structured diagnostics for:

* Frame begin/end
* Resize events
* Surface reconfigure
* Draw call count
* Batch statistics
* Present duration

Diagnostics must be:

* Non-blocking
* Toggleable
* Structured

---

# 13. Thread Readiness

Renderer currently runs on main thread.

Architecture must allow later migration to render thread using:

* Immutable snapshots
* Atomic or double-buffered snapshot swap
* No shared mutable state

Thread separation must not require core redesign.

---

# Design Priority

Rendering system must remain:

* Explicit
* Deterministic (simulation layer)
* Observable
* Backend-isolated
* Extendable
* Resize-stable
* Thread-ready

This document defines the baseline constraints for future rendering evolution.

# Window & Panel Policies v1.0

This document defines the architectural policies governing the engine's windowing and panel subsystem.

The window layer is responsible for OS window creation, event loop integration, DPI handling, and surface provisioning for the renderer.

---

# 1. Responsibility Boundaries

The Window/Panel subsystem is responsible for:

* Creating and destroying OS windows
* Managing DPI / scaling information
* Providing a rendering surface to the renderer backend
* Dispatching raw input events to the Input subsystem
* Handling OS-level resize events

It is NOT responsible for:

* Rendering logic
* Simulation timing
* Audio
* Asset management

---

# 2. Renderer Interaction Contract

* Window layer produces a `Surface` (or equivalent handle).
* Renderer attaches to provided surface.
* Renderer must not directly manage window lifecycle.

Direction of dependency:

WindowLayer → Surface → RenderBackend

Renderer must never create or own the OS window.

---

# 3. Backend Isolation

Initial backend: GLFW.

Policies:

* Windowing API must not leak into engine core.
* Engine core must not depend on GLFW types.
* Window backend must be replaceable (e.g., SDL, wgpu-native, platform-specific).

---

# 4. Resize Policy

On resize or DPI change:

* Window layer emits resize event.
* Renderer reconfigures surface.
* Simulation is unaffected.

Resize must not force renderer/device recreation.

---

# 5. Event Loop Ownership

Window layer owns OS event polling.

It must:

* Poll OS events
* Translate into normalized engine events
* Forward to Input subsystem

Renderer must not drive OS event loop.

---

# 6. DPI & Coordinate Policy

* Window operates in logical units.
* Renderer configured in physical pixels.
* DPI scale explicitly passed to renderer on resize.

Implicit scaling is not allowed.

---

# 7. Thread Readiness

Window must initially run on main thread.

Design must allow:

* Renderer potentially running in separate thread later
* Surface creation and event dispatch remaining stable

---

# 8. Diagnostics Integration

Window subsystem must emit structured diagnostics events for:

* Resize
* DPI changes
* Focus changes
* Window minimize/restore

Diagnostics must be non-blocking.

---

# Design Goals

The window subsystem must remain:

* Thin
* Replaceable
* Deterministic
* Explicit
* Renderer-independent

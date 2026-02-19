# Input Policies v1.0

This document defines the architectural policies governing the input subsystem.

The input subsystem translates raw device events into deterministic engine commands.

---

# 1. Responsibility

Input subsystem is responsible for:

* Receiving raw input events from window layer
* Normalizing device-specific data
* Mapping inputs to engine-level actions
* Providing frame-consistent input state to simulation

It is NOT responsible for:

* Rendering
* Window ownership
* Simulation logic
* Direct gameplay mutations

---

# 2. Backend Isolation

Initial backend: GLFW event system.

Policies:

* GLFW types must not leak into simulation core.
* Input backend must be replaceable (e.g., SDL, HID libraries, platform APIs).

---

# 3. Deterministic Frame Model

Input is processed per frame.

Workflow:

1. Window polls raw events
2. Input subsystem normalizes events
3. Final input state snapshot exposed to simulation

Simulation reads stable input state for that frame.

No mid-frame mutation allowed.

---

# 4. Input Snapshot Contract

Each frame exposes:

* Keyboard state
* Mouse state
* Controller state (if enabled)
* Action map resolution

Input snapshot must be immutable during simulation step.

---

# 5. Action Mapping Policy

Input must support action abstraction:

* Physical input → Logical action

Engine core consumes actions, not raw keycodes.

Allows:

* Rebinding
* Backend independence
* Clean replay behavior

---

# 6. Thread Readiness

Input initially runs on main thread.

Design must allow:

* Future event buffering for multi-threaded simulation
* Snapshot-based input exchange

---

# 7. Replay Compatibility

Input subsystem must allow:

* Recording logical action stream
* Replaying deterministic action stream

Simulation must not depend on physical device state.

---

# 8. Diagnostics Integration

Input subsystem must emit structured diagnostics for:

* Event frequency
* Device connect/disconnect
* Mapping conflicts

Diagnostics must be non-blocking.

---

# Design Goals

Input subsystem must remain:

* Deterministic
* Snapshot-driven
* Backend-isolated
* Simulation-neutral
* Replaceable

# Audio Policies v1.0

This document defines the architectural policies governing the audio subsystem.

The audio subsystem is responsible for sound device management, spatialization, and mixing.

---

# 1. Responsibility

Audio subsystem is responsible for:

* Managing audio device lifecycle
* Sound buffer management
* Mixing and spatialization
* Applying attenuation and positional logic
* Submitting final audio output to device backend

It is NOT responsible for:

* Rendering
* Simulation timing
* Asset loading IO (handled by asset subsystem)

---

# 2. Backend Isolation

Initial backend: OpenAL.

Policies:

* OpenAL types must not leak into engine core.
* Backend must be replaceable (e.g., SDL audio, custom mixer, other APIs).
* Audio API exposed to simulation must remain backend-neutral.

---

# 3. Audio Model

Audio model must support:

* Listener state (position, orientation)
* Sound emitters with world positions
* Distance attenuation
* Basic stereo/3D spatialization

Simulation provides emitter positions; audio subsystem performs spatial processing.

---

# 3A. Geometry & Environmental Extensibility Policy

The audio subsystem must remain geometry-agnostic.

Policies:

* Audio backend must not directly query physics or world geometry.
* Audio subsystem must not perform raycasts or spatial queries itself.
* Simulation is responsible for computing any geometry-based modifiers.

Simulation may compute and submit optional environmental modifiers such as:

* Occlusion factor
* Obstruction factor
* Reverb zone identifier
* Custom gain multipliers

Audio subsystem applies provided modifiers but does not derive them.

This preserves subsystem isolation and allows future environmental audio features without coupling audio to physics or scene graph implementations.

Audio model must support:

* Listener state (position, orientation)
* Sound emitters with world positions
* Distance attenuation
* Basic stereo/3D spatialization

Simulation provides emitter positions; audio subsystem performs spatial processing.

---

# 4. Timing Model

Audio runs continuously and independently from rendering.

Policies:

* Audio device must not block simulation.
* No audio operations allowed during simulation-critical sections.
* Audio updates may occur at fixed or device-driven interval.

---

# 5. Snapshot & Command Policy

Simulation submits audio commands or state updates per frame:

* Play
* Stop
* Update emitter position
* Set listener transform

Audio subsystem consumes commands asynchronously.

---

# 6. Mixing Strategy

Initial implementation:

* Delegate spatialization and mixing to OpenAL.
* Avoid custom DSP until required by scale.

Advanced mixing or DSP graph may be added later as backend extension.

---

# 7. Thread Readiness

Audio may internally use its own callback or worker thread.

Simulation must interact through:

* Immutable commands
* Lock-free or queued message passing

No shared mutable state allowed.

---

# 8. Determinism Policy

* Simulation determinism is required.
* Audio playback timing need not be bit-identical across machines.
* Audio events are driven by deterministic command stream.

---

# 9. Diagnostics Integration

Audio subsystem must emit structured diagnostics for:

* Active emitters
* Channel usage
* Backend errors
* Device state changes

Diagnostics must be non-blocking.

---

# Design Goals

Audio subsystem must remain:

* Backend-isolated
* Replaceable
* Spatially aware
* Thread-safe
* Simulation-decoupled

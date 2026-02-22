# Engine API Contract Model Policy

## 1) Classification Rule

Every public `engine.api.*` contract must be classified as exactly one of:

1. Subsystem Role
2. Capability Slice
3. Data Shape
4. Typing Aid (internal)

No contract may exist without classification.

## 2) Subsystem Role (Use `ABC`)

Definition:
A contract represents a runtime-owned, replaceable engine subsystem.

Characteristics:

- Has lifecycle
- Injected via DI
- Long-lived object
- Acts as an architectural actor
- Appears in composition wiring
- Is resolved from container
- Is central to engine execution

Examples:

- `RendererPort`
- `WindowPort`
- `UpdateLoop`
- `EventBus`
- `UIFramework`
- `EngineHost`
- `RuntimeContext` (if behavior-centric)

Rule:
These must be defined as abstract base classes.

```python
from abc import ABC, abstractmethod
```

Constraints:

- No `Protocol`
- Explicit inheritance required
- No reflection checks
- No duck typing
- Must be instantiated only via composition container

Rationale:
Subsystem roles are architectural identities, not structural shapes.

## 3) Capability Slice (Use `Protocol` + `@runtime_checkable`)

Definition:
A contract represents a behavior fragment that may be optionally supported.

Characteristics:

- Not a full subsystem
- Small interface
- Used to remove reflection
- Often capability-scoped (for example, `SupportsX`)
- Not lifecycle-owning

Examples:

- `SupportsResize`
- `SupportsRequestDraw`
- `SupportsTelemetryEmit`
- `SupportsDesignResolution`

Rule:
These must be runtime-checkable protocols.

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsX(Protocol):
    ...
```

Constraints:

- Used only to replace `hasattr`/`getattr` checks
- Checked via `isinstance(obj, SupportsX)`
- Never used as injection root
- Should remain minimal (1-3 methods ideally)

Rationale:
Capability slices are structural behavior agreements.

## 4) Data Shape (No `@runtime_checkable`, Prefer Typed DTO)

Definition:
A contract describes data structure, not behavior.

Characteristics:

- Payload objects
- Snapshot structures
- Event data
- Flow payload
- Immutable value-like types

Examples:

- `FlowPayload`
- `ScreenData`
- `RenderDataValue`
- DTO classes

Rule:
Use one of:

- `dataclass`
- `TypedDict`
- Plain typed classes
- `Protocol` only if necessary for static typing

Never:

- `@runtime_checkable`
- `ABC`

Rationale:
Runtime structural checks add no safety for data; static typing is sufficient.

## 5) Typing Aid (Internal Only)

Definition:
Type-level abstraction helper.

Characteristics:

- Not part of public API
- Not used at runtime
- Purely to help mypy

Rule:

- Use `Protocol`
- No `@runtime_checkable`
- No `ABC`
- Keep internal to module

## 6) Explicit Prohibitions

- Subsystem roles must not be `Protocol`.
- Capability slices must not be `ABC`.
- Data contracts must not be runtime-checkable.
- Reflection (`hasattr`, `getattr`) is forbidden for required paths.

Required alternatives:

- `ABC` identity
- `Protocol` capability checks

## 7) Injection Rule

Only subsystem roles (ABC types) may be:

- Registered in DI container
- Requested via resolver
- Declared as constructor-injected services

Capability slices must never be DI-resolved standalone.

## 8) Boundary Enforcement Principle

At the Game <-> Engine boundary:

- Subsystem roles are nominal (`ABC`)
- Capability fragments are structural (`Protocol`)
- Data flows are typed values (DTO)

This preserves:

- Clear architectural ownership
- Strong injection identity
- Minimal reflection
- Clear replaceability semantics

## 9) Summary Table

| Category | Type System | Runtime Checkable | DI Injectable | Purpose |
| --- | --- | --- | --- | --- |
| Subsystem Role | `ABC` | Native | Yes | Architectural actor |
| Capability Slice | `Protocol` | Yes | No | Behavior fragment |
| Data Shape | Typed DTO / `Protocol` | No | No | Value structure |
| Typing Aid | `Protocol` | No | No | Static-only |

## 10) Meta Rule

If removing inheritance from a contract does not change architectural meaning, it should not be an `ABC`.

If failure to explicitly inherit should be considered a structural violation, it must be an `ABC`.

That is the decision pivot.

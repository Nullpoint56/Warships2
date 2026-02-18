# Import Boundaries

## Rules

1. Engine must not import Warships.
2. Warships game code imports Engine only via `engine.api` modules.
3. `engine.api` top-level imports must not depend on `engine.runtime` or `engine.rendering`.
4. Runtime bootstrap entrypoint for apps is `engine.api.hosted_runtime`.
5. Wildcard imports (`from x import *`) are forbidden in engine and game code.

## Rationale

- Prevent circular imports across package roots.
- Keep engine internals replaceable without touching game code.
- Preserve strict API/port architecture between engine and app.

## Enforcement

Automated checks live in:

- `tests/engine/unit/api/test_import_boundaries.py`

These tests fail the build if a boundary is violated.

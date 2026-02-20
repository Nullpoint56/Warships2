# Asset Management Policies v1.0

This document defines architectural boundaries for asset ownership, loading, and runtime usage.

## 1. Responsibility Boundaries

Asset management subsystem is responsible for:
- locating, loading, and validating asset sources,
- handling asset formats and metadata,
- lifecycle management for asset handles/references,
- caching and invalidation policy.

It is NOT responsible for:
- simulation logic,
- window/event loop ownership,
- frame scheduling,
- gameplay state mutation.

## 2. Renderer Ownership Boundary

Renderer must:
- consume immutable asset handles/references prepared by asset management,
- avoid direct gameplay asset I/O in runtime frame path.

Renderer must not:
- own global asset catalogs,
- perform general-purpose asset discovery or loading policies for game content.

## 3. Temporary Migration Exception (Text Fonts)

During the wgpu migration only:
- renderer may perform limited OS/system font discovery to satisfy text rendering parity,
- renderer may own glyph atlas cache state required for text draw submission.

Constraints for this exception:
- scope is limited to text font resolution and glyph raster cache,
- no expansion into generic asset catalog responsibilities,
- failure behavior in non-headless mode must be explicit and hard-fail with diagnostics if no suitable system font is found.

This exception should be revisited when a dedicated asset/font service is introduced.

## 4. Handle Contract

Assets used by runtime systems should be referenced through stable handles or immutable descriptors.
Subsystem boundaries should prevent backend-specific types from leaking into engine API contracts.

## 5. Determinism and Replay

Runtime asset usage must be deterministic for a given resolved handle set.
Simulation/replay paths must not depend on nondeterministic asset discovery at frame time.

## 6. Diagnostics

Asset subsystem diagnostics should include:
- load success/failure events,
- missing asset details,
- fallback resolution decisions,
- cache hit/miss indicators.

Diagnostics must be non-blocking and structured.

## 7. Evolution Path

Short term:
- keep migration exception for system-font text support.

Medium term:
- move font/source resolution behind dedicated asset/font service,
- keep glyph GPU cache as renderer-internal implementation detail.

Long term:
- enforce strict no-I/O renderer runtime path beyond explicit, approved exceptions.

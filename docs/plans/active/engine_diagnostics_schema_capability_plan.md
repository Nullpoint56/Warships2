# Engine Diagnostics Schema and Capability Architecture Plan

Date: 2026-02-21  
Status: Active  
Scope: Redesign engine diagnostics data contract to be schema-first and tool-agnostic.

## Problem

Current diagnostics toggles and payloads are functional but too coupled:

1. Toggle semantics are not fully isolated by diagnostics domain.
2. Some tools implicitly depend on specific events without an explicit capability contract.
3. Payload fields are evolving, but schema ownership and compatibility policy are not centralized.

## Goals

1. Make diagnostics schema a first-class engine contract.
2. Decouple producer capabilities from consumer tools.
3. Keep runtime overhead predictable via explicit budgets and sampling.
4. Preserve evolvability through versioned payloads and compatibility rules.

## Non-Goals

1. Building a new UI tool in this plan.
2. Rewriting every existing diagnostics payload in one step.

## Principles

1. Engine owns schemas; tools consume declared capabilities.
2. Capabilities are domain-driven, not tool-driven.
3. Sampling and budget controls are producer-side.
4. Every payload has a declared schema version.

## Target Architecture

### A. Event Envelope Contract

All emitted diagnostics records use a stable envelope:

- `schema_version`
- `ts_utc`
- `tick`
- `category`
- `name`
- `level`
- `value`
- `metadata`

### B. Capability Registry

Introduce capability IDs, e.g.:

- `diag.events.core`
- `diag.metrics.frame`
- `diag.profiling.frame`
- `diag.profiling.spans`
- `diag.render.stage`
- `diag.render.profile`
- `diag.memory.process`
- `diag.replay`
- `diag.crash`

Each capability declares:

- producer module(s)
- schema names emitted
- default sampling/rate budget
- required env toggles

### C. Schema Registry

Engine-side registry maps `category/name` to typed schema descriptors:

- required fields
- optional fields
- units and semantic notes
- migration notes (if superseded)

### D. Runtime Profiles

Define explicit profile presets:

- `minimal_live`
- `dev_fast`
- `dev_deep`
- `release_like`

Each profile is a capability + budget bundle.

## Execution Phases

### Phase 1: Contract Foundation

Implementation:

1. Add diagnostics schema registry module.
2. Add capability registry module.
3. Define envelope schema version policy.

Exit:

1. Registry exists and is referenced by diagnostics emission paths.

### Phase 2: Capability-Driven Runtime Config

Implementation:

1. Replace ad hoc toggle interpretation with capability/budget resolver.
2. Add named runtime diagnostics profiles.
3. Expose active profile + capabilities in diagnostics snapshot.

Exit:

1. Tools can inspect which capabilities are active.

### Phase 3: Producer Migration

Implementation:

1. Migrate frame/render/profiling/replay/crash emitters to registered schemas.
2. Add lightweight emit-time validation in debug profiles.

Exit:

1. Core emitters are registry-backed and versioned.

### Phase 4: Tool Contract Migration

Implementation:

1. Update engine monitor and inspector to consume capability metadata.
2. Show explicit capability-missing messages instead of silent blanks.

Exit:

1. Tools degrade gracefully and predictably when capabilities are off.

### Phase 5: Compatibility and Governance

Implementation:

1. Add schema compatibility test suite.
2. Add deprecation policy for renamed/removed diagnostics fields.
3. Document migration checklist for new diagnostics events.

Exit:

1. Schema evolution is test-enforced and documented.

## Acceptance Criteria

1. Diagnostics toggles map to domain capabilities, not specific tools.
2. Active capabilities are introspectable at runtime.
3. Monitor/inspector can clearly report missing capabilities.
4. Schema compatibility tests prevent accidental breaking changes.
5. Runtime profile overhead is measurable and reproducible.

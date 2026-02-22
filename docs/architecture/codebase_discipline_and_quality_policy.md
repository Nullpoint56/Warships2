# Engine Codebase Discipline & Hybrid Quality Policy

## Scope

Applies to all packages under `engine.*`.
Applies to all pull requests.
CI enforcement is mandatory.

---

# 1. Deterministic Static Enforcement (Hard Gates)

These checks are blocking. No override without emergency procedure.

## 1.1 Layered Architecture Enforcement

Tool: **import-linter + bootstrap ownership check**

Rules:

* `engine.api` cannot import `engine.runtime` or `engine.platform`
* `engine.domain` cannot import `engine.api`
* `engine.sdk` cannot import `engine.runtime` or `engine.platform`
* Runtime-owned composition is allowed to depend on `engine.sdk` and `engine.api`
* No cross-layer shortcut imports under layered order:
  `engine.bootstrap -> engine.runtime -> engine.sdk -> engine.api -> engine.domain -> engine.platform`

CI Command:

```
lint-imports
```

Additional blocking command:

```
python scripts/check_bootstrap_wiring_ownership.py
```

## 1.2 No Import Cycles

Tool: **`scripts/check_import_cycles.py`**

* SCC size must equal 1
* No cyclic dependencies allowed

Enforced command:

```
python scripts/check_import_cycles.py
```

Budget command (monotonic non-regression):

```
python scripts/check_import_cycles.py --allow-cycles --baseline tools/quality/budgets/import_cycles_baseline.json --json-output docs/architecture/audits/static_checks/latest/import_cycles_metrics.json
```

## 1.3 API Runtime Factory Boundary

Tool: **`scripts/check_api_runtime_factories.py`**

Rules:

* In `engine.api.*`, no `create_*` / `run_*` function may import from `engine.runtime.*`

Enforced command:

```
python scripts/check_api_runtime_factories.py
```

## 1.4 Strict Type Contracts

Tool: **mypy --strict**

Contract model authority:

* `docs/architecture/engine_api_contract_model_policy.md`

Configuration requirements:

* `strict = true`
* `disallow_untyped_defs = true`
* `disallow_any_generics = true`
* `no_implicit_optional = true`
* `warn_unused_ignores = true`

Rules:

* All public APIs typed
* Cross-layer boundaries use `Protocol`
* No hidden duck typing across layers

## 1.5 Complexity Budgets

Tool: **xenon**

Rules:

* Max absolute complexity: B
* Max module complexity: A
* Max average complexity: A

File Limits:

* Soft: 600 LOC
* Hard: 900 LOC

Enforced command:

```
python scripts/check_engine_file_limits.py --soft 600 --hard 900
```

## 1.6 Barrel Export Budget

Tool: **`scripts/check_barrel_exports.py`**

Rules:

* `engine/api/__init__.py` export count budget: 120
* `engine/runtime/__init__.py` export count budget: 30
* No mixed layer barrel imports (`engine.api.*` and `engine.runtime.*` in the same barrel)

Enforced command:

```
python scripts/check_barrel_exports.py
```

## 1.7 Config Ownership / Env Read Placement

Tool: **`scripts/check_env_read_placement.py`**

Rules:

* Env reads (`os.environ`, `os.getenv`, `environ.get`) are only allowed in designated config/bootstrap modules

Enforced command:

```
python scripts/check_env_read_placement.py
```

## 1.8 Broad Exception Policy

Tool: ruff + semgrep

Rules:

* Bare `except:` forbidden
* `except Exception` requires logging
* Silent swallowing forbidden

Enforced commands:

```
ruff check engine --select E722,BLE001
semgrep --error --config tools/quality/semgrep/broad_exception_policy.yml engine
```

## 1.9 Domain Literal Leakage (Lexical)

Tool: semgrep

* Block explicit title-specific terminology in `engine.*`

Enforced command:

```
semgrep --error --config tools/quality/semgrep/domain_literal_leakage.yml engine
```

## 1.10 Protocol Boundary Integrity

Tool: semgrep

Rules:

* No opaque provider APIs (`provider: object`) in boundary APIs
* Required protocol/capability surface must be enforced for factory/provider boundaries
* Reflection-driven provider checks (`hasattr(...)`) in boundary code are blocked

Enforced command:

```
semgrep --error --config tools/quality/semgrep/protocol_boundary_rules.yml engine
```

## 1.11 Domain Semantic Hardening

Tool: **`scripts/check_domain_semantic_leakage.py`**

Rules:

* Ban domain-semantic literals in core engine APIs (policy regex set in script)

Enforced command:

```
python scripts/check_domain_semantic_leakage.py
```

## 1.12 Duplication Threshold

Tool: jscpd

* Duplication threshold <= 5%
* Executed via Node: `npx jscpd --threshold 5 engine`

## 1.13 Duplicate Cluster Gate

Tool: **`scripts/check_duplicate_cluster.py`**

Rules:

* Zero-tolerance scoped duplicate gate for `engine/api/ui_primitives.py` and `engine/ui_runtime/**`

Enforced command:

```
python scripts/check_duplicate_cluster.py
```

## 1.14 Boundary DTO Purity Gate

Tool: **`scripts/check_boundary_dto_purity.py`**

Rules:

* Public `engine.api.*` contracts cannot use `object`/`Any` boundary typing.
* Public `engine.api.*` contracts cannot reference `engine.runtime.*` types in annotations.

Enforced command:

```
python scripts/check_boundary_dto_purity.py
```

## 1.15 Feature/Env Flag Registry Hygiene

Tool: **`scripts/check_feature_flag_registry.py`**

Rules:

* Every env/feature flag used in engine code must exist in `tools/quality/budgets/feature_flags_registry.json`.
* Each registry entry must include: `owner`, `rationale`, `remove_by`, `status`.
* `remove_by` must use `YYYY-MM-DD` format and must not be in the past.

Enforced command:

```
python scripts/check_feature_flag_registry.py
```

## 1.16 State Mutation Ownership Guard

Tool: **`scripts/check_state_mutation_ownership.py`**

Rules:

* No mutable module-level globals (`list`/`dict`/`set` or constructors) in engine modules.
* No `global` writes in engine modules.

Enforced command:

```
python scripts/check_state_mutation_ownership.py
```

## 1.17 Exception Observability Semantics

Tool: **`scripts/check_exception_observability.py`**

Rules:

* Broad exception handlers (`except:` and `except Exception`) must include explicit error observability.
* Accepted forms: `logger.exception(...)` or `logger.error|warning|critical(..., exc_info=True)`.

Enforced command:

```
python scripts/check_exception_observability.py
```

## 1.18 Public API Surface Stability

Tool: **`scripts/check_public_api_surface.py`**

Rules:

* Public API surface from `engine/api/__init__.py::__all__` is baseline-gated.
* Any addition/removal requires explicit baseline update in `tools/quality/budgets/engine_api_surface_baseline.txt`.

Enforced command:

```
python scripts/check_public_api_surface.py
```

Baseline update command (intentional API change only):

```
python scripts/check_public_api_surface.py --update-baseline
```

## 1.19 Manual Performance Evaluation

Tool: manual performance evaluation (profiling + representative scenario timing)

* Performance evaluation is required for performance-critical changes.
* Results must be documented in the plan/PR review output.
* This step is manual and not CI-gated by benchmark tooling.

## 1.20 Unified CI Gate Entry Point

Tool: **`scripts/policy_static_checks.py`**

Rules:

* CI must run the unified static gate runner.
* Per-tool checks above are authoritative and must remain aligned with the runner implementation.

CI command:

```
python scripts/policy_static_checks.py
```

---

Below is a redesigned, hardened version of your **LLM Semantic Governance Layer**.

It converts the review from “advisory commentary” into a structured architectural analysis instrument.

This version enforces:

* Evidence binding
* Root-cause classification
* Severity normalization
* Confidence scoring
* Systemic vs local issue distinction
* Actionable refactor direction

---

# 2. LLM Semantic Governance Layer

**(Mandatory Structured Review — Architectural Advisory)**

LLM review is required for all PRs affecting:

* `engine/api`
* `engine/runtime`
* `engine/rendering`
* `engine/window`
* `engine/sdk`
* cross-layer modifications
* host, renderer, lifecycle, diagnostics, or config paths

LLM findings are advisory unless marked **Critical Architecture Risk**.

---

# 2.0 Output Contract (Mandatory)

Every finding MUST follow this structure:

```
[Finding ID: <CATEGORY>-###]

Category: <One of the categories below>
Location:
  - File(s):
  - Line range (if identifiable):
Risk Level:
  - Informational
  - Medium Structural Risk
  - High Structural Risk
  - Critical Architecture Risk
Root Cause Classification:
  - Structural layering issue
  - Contract weakness
  - Ownership drift
  - Performance topology issue
  - Semantic domain bias
  - Lifecycle sequencing risk
  - Configuration ownership drift
Evidence:
  - Concrete code behavior reference
  - Why this is systemic (not stylistic)
Impact:
  - What will degrade over time if not addressed
Proposed Structural Direction:
  - High-level corrective path (not cosmetic fix)
Confidence:
  - Low / Medium / High
```

Rules:

* No stylistic feedback.
* No naming-only suggestions.
* No formatting comments.
* No micro-optimizations unless in performance section.
* No speculative criticism without code evidence.

All flags must include file references.

---

# 2.1 API Ergonomics Review

LLM must:

1. Show a realistic usage flow of the API being modified.
2. Identify call-site verbosity.
3. Identify unnecessary multi-step construction.
4. Evaluate config propagation.
5. Detect builder/factory verbosity.

Flag when:

* Common tasks require excessive orchestration.
* Object graph assembly leaks into domain layer.
* API abstraction does not meaningfully simplify runtime.

Additional required output:

* Is the verbosity inherent or architectural?
* Does ergonomics degrade scalability?

---

# 2.2 Domain Leakage by Meaning

LLM must evaluate:

* Hidden gameplay assumptions.
* Domain-biased defaults.
* Semantic bias in generic abstractions.
* Title-specific literals.

Flag when:

* Behavior implies naval/grid/2D/game-specific semantics.
* Engine API contains domain-specific vocabulary.
* Runtime contains game-level flags.

Additional requirement:

* Distinguish semantic bias from neutral parameterization.

---

# 2.3 Misleading Abstractions

LLM must check:

* Does abstraction match responsibility?
* Does class name misrepresent behavior?
* Does protocol hide required capabilities?
* Does abstraction leak implementation detail?

Flag when:

* “Host” acts as multi-service container.
* Generic names wrap specific behaviors.
* Required-path reflection exists.

Must include:

* Whether abstraction reduction or split is preferable.

---

# 2.4 Performance Risk Heuristics

LLM must analyze:

* Object reconstruction inside loops.
* Per-frame container rebuilds.
* Snapshot transform overhead.
* Nested dispatch layers.
* N² risk.

Flag when:

* Immutable reshaping happens every frame.
* Map/dict rebuilt per event.
* Reflection in hot path.
* Branch-dense logic inside draw/update path.

Must include:

* Whether issue is hot-path likely or theoretical.
* Estimated runtime degradation risk over growth.

---

# 2.5 Error Semantics Consistency

LLM must evaluate:

* Exception policy consistency across layers.
* Presence of silent fallbacks.
* Retry policy centralization.
* Exception leakage beyond boundary.

Flag when:

* Broad exception catch without telemetry.
* Runtime transforms errors across layers.
* Mixed paradigms inside same subsystem.

Must include:

* Whether error model is deterministic or permissive.
* Long-term observability risk.

---

# 2.6 Abstraction Depth Assessment

LLM must evaluate:

* Wrapper thickness relative to value.
* Indirection layers without logic.
* Barrel export misuse.
* API-to-runtime forwarding functions.

Flag when:

* Proxy modules forward directly.
* Indirection multiplies import coupling.
* Over-factored micro-layers exist.

Must distinguish:

* Necessary decoupling from gratuitous layering.

---

# 2.7 Configuration Ownership Drift (Semantic)

LLM must evaluate:

* Config logic inside hot path modules.
* Duplicate env parsing logic.
* Feature flag proliferation.
* Runtime behavior controlled by ambient state.

Flag when:

* Config decisions are evaluated repeatedly.
* Env reads scattered.
* Flags not injected but pulled.

Must include:

* Whether drift increases unpredictability under growth.

---

# 2.8 Duplication and Ownership Overlap

LLM must detect:

* Parallel implementations across packages.
* API/runtime dual ownership.
* Similar logic in diagnostics/runtime.
* Serialization duplication.

Flag when:

* Logic duplicated across layers for convenience.
* Similar algorithm with slight variation exists.

Must include:

* Whether duplication indicates boundary confusion.

---

# 2.9 Feature Growth Stress Test

LLM must simulate:

* Adding Audio subsystem
* Adding Networking subsystem
* Adding Asset streaming subsystem

Answer:

* Where would feature attach?
* Which module would grow?
* Would host expand?
* Would SCC likely increase?

Flag:

* Centralized fragility
* Architecture cannot absorb subsystem without structural edits

---

# 2.10 Replaceability Audit

LLM must evaluate:

* Can renderer be replaced?
* Can window backend be replaced?
* Can update loop be replaced?
* Can event bus be replaced?

Flag:

* Hidden dependency flows
* Runtime-to-implementation knowledge leakage
* Implicit coupling via behavior ordering

---

# 2.11 Architectural Entropy Forecast

LLM must answer:

* What subsystem currently attracts new responsibilities?
* Which module will likely exceed budget first?
* Where is entropy concentration forming?
* What will become future God module?

This converts review into predictive governance.

---

# 2.12 Summary Output Block

Each review must conclude with:

```
Architecture Stability Summary:
- Layering Integrity: Stable / Slight Erosion / Structural Risk
- Coupling Gradient: Healthy / Growing / High
- Replaceability: Strong / Moderate / Weak
- Growth Resilience: Good / Concerning / Fragile
- Overall Risk Rating: 1–10
```

---

# Reviewer Behavior Rules

LLM must:

* Never rewrite code unless asked.
* Never propose renames as primary solution.
* Prefer structural decomposition over local patches.
* Not repeat static check findings unless giving new meaning-level interpretation.
* Avoid trivial remarks.

---

# Governance Rule

If any finding is marked:

> Critical Architecture Risk

Then:

* It must reference structural layering or boundary violation.
* It requires human review acknowledgment before merge.

---

# 3. Governance Principles

* Static tools enforce structure and invariants.
* LLM review enforces semantic clarity and architectural coherence.
* No policy relies solely on probabilistic reasoning.
* Performance-critical code must have manual performance-evaluation backing.
* Architecture violations are blocked early, not debated post-merge.

---

# 4. Minimum Viable Toolchain

Required:

* import-linter
* mypy
* xenon
* ruff
* semgrep
* jscpd
* pytest
* nodejs (for `npx jscpd`)
* policy scripts under `scripts/check_*.py` and `scripts/policy_static_checks.py`
LLM:

* Structured semantic review

---

This document defines non-negotiable architectural discipline for long-term engine evolution.

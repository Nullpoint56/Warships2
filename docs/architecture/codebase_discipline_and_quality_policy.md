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
* Only `engine.bootstrap` may wire concrete implementations
* No cross-layer shortcut imports

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

# 2. LLM Semantic Governance Layer (Advisory, Required Review Output)

These checks are mandatory for review but not auto-blocking unless marked "critical".

Each PR affecting engine core must be reviewed by LLM agent with structured output.

---

## 2.1 API Ergonomics Review

LLM must answer:

* Show a typical user workflow for this API.
* Is it unnecessarily verbose?
* Are common operations multi-step when they could be single-step?
* Are parameter names consistent and intention-revealing?
* Is configuration leaking into call sites?

Flag:

* Boilerplate-heavy usage
* Verbose initialization chains
* Parameter inconsistency

---

## 2.2 Domain Leakage by Meaning

LLM must answer:

* Does this module embed assumptions about specific gameplay mechanics?
* Are defaults biased toward one domain profile?
* Are abstractions secretly tuned for naval/grid/2D assumptions?

Flag:

* Implicit domain coupling
* Non-neutral default semantics

---

## 2.3 Misleading Abstractions

LLM must evaluate:

* Does the class name match actual responsibility?
* Is the abstraction too generic or too specific?
* Are protocols minimal and correct?
* Are internal details leaking through public API?

Flag:

* Overly broad abstraction
* Narrow abstraction disguised as generic
* Protocol boundary weakness

---

## 2.4 Performance Risk Heuristics

LLM must analyze:

* What objects are rebuilt per call?
* Are containers reconstructed in hot paths?
* Is deep copying done unnecessarily?
* Are nested loops risking N² or worse?

Flag:

* Snapshot rebuild churn
* Repeated map/dict reconstruction
* Excessive temporary object creation

---

## 2.5 Inconsistent Error Semantics

LLM must evaluate:

* Are exception models consistent across layers?
* Is retry logic centralized?
* Are errors silently transformed?
* Are internal exceptions leaking outside boundary?

Flag:

* Mixed error paradigms
* Silent fallback logic

---

## 2.6 Abstraction Depth Assessment

LLM must evaluate:

* Are there too many thin wrapper layers?
* Is indirection excessive relative to feature size?
* Is boilerplate dominating core logic?

Flag:

* Over-engineering
* Wrapper chains without value

---

## 2.7 Config Ownership Drift (Semantic)

LLM must evaluate:

* Are configuration values creeping into runtime logic?
* Is feature flag usage proliferating?
* Are default behaviors environment-dependent in subtle ways?

Flag:

* Hidden config coupling
* Runtime behavior dependent on ambient state

---

## 2.8 Refactor Opportunity Identification

LLM must provide:

* Modules that should be split
* Extractable shared behaviors
* Redundant layers
* Collapsible boilerplate sections

Include:

* Concrete refactor suggestion
* Risk level

---

# 3. Hybrid Review Workflow

## PR Requirements

PR must:

1. Pass all static CI gates.
2. Include LLM structured review output.
3. Address critical LLM flags before merge.

## Structured LLM Output Format

For each category:

* Observation
* Risk Level (Low / Medium / High)
* Concrete Recommendation
* Confidence Estimate

---

# 4. Governance Principles

* Static tools enforce structure and invariants.
* LLM review enforces semantic clarity and architectural coherence.
* No policy relies solely on probabilistic reasoning.
* Performance-critical code must have manual performance-evaluation backing.
* Architecture violations are blocked early, not debated post-merge.

---

# 5. Minimum Viable Toolchain

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

* Structured PR semantic review agent

---

This document defines non-negotiable architectural discipline for long-term engine evolution.


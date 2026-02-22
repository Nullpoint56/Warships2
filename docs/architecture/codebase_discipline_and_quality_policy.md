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

Tool: import-linter

* SCC size must equal 1
* No cyclic dependencies allowed

## 1.3 Strict Type Contracts

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

## 1.4 Complexity Budgets

Tool: **xenon**

Rules:

* Max absolute complexity: B
* Max module complexity: A
* Max average complexity: A

File Limits:

* Soft: 600 LOC
* Hard: 900 LOC

## 1.5 Broad Exception Policy

Tool: ruff + semgrep

Rules:

* Bare `except:` forbidden
* `except Exception` requires logging
* Silent swallowing forbidden

## 1.6 Domain Literal Leakage

Tool: semgrep

* Block explicit title-specific terminology in `engine.*`

## 1.7 Duplication Threshold

Tool: jscpd

* Duplication threshold <= 5%
* Executed via Node: `npx jscpd --config .jscpd.json`

## 1.8 Manual Performance Evaluation

Tool: manual performance evaluation (profiling + representative scenario timing)

* Performance evaluation is required for performance-critical changes.
* Results must be documented in the plan/PR review output.
* This step is manual and not CI-gated by benchmark tooling.

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
* semgrep
* jscpd
* pytest
* nodejs (for `npx jscpd`)
LLM:

* Structured PR semantic review agent

---

This document defines non-negotiable architectural discipline for long-term engine evolution.


# Architecture refactoring template

This document is a template for doing architectural refactors of the engine. It contains two main sections
- Static Check Findings: Signals collected from static checkers
- LLM Check Findings: LLM executed check signals

Each Check finding part contains these fields:
- Evaluations: Raw output interpretations (very verbose to not miss details)
- Investigation: Raw output signals are rarely the ones we need to react on. They usually hide deeper issues. Because of that, investigation section is an investigation of why the Raw check signals appeared.
- Proposed fixes: Investigation reveals root causes, proposed fixes are higher level decisions and documented approaches on how the identified root causes will be fixed.
- Refactoring Phase-Plan: Proposed fixes will be broken down from high level plans into low level actionable, phase by phase fix executions.

## Static Check Findings

### Evaluations

### Investigation

### Proposed fixes

### Refactoring Phase-Plan


## LLM Check Findings

### Evaluations

### Investigation

### Proposed fixes

### Refactoring Phase-Plan
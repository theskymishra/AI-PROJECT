# PHASE 6 — KNOWLEDGE ENGINE, FORWARD CHAINING AND FOL

**Status: implementation complete pending the repository test run.**

Phase 6 adds an explainable symbolic layer on top of Phase 5's probabilistic
risk estimates. It does not replace the HMM, Bayesian Network or A*; it turns
selected numeric conclusions into explicit facts and derives higher-level
facts with Horn-style rules.

## Pipeline

```text
Sensors → HMM → Bayesian Network → P(failure)
                                  ↓
                         HighFailureProb(R)
                                  ↓
                       Forward-chaining KB
                         ↓             ↓
                    Unsafe(R)       Avoid(R)
                         ↓
                    A* soft penalty
```

The threshold is `KNOWLEDGE_HIGH_FAILURE_THRESHOLD = 0.60`, matching the
Phase 5 hand-off and the Phase 7 CSP requirement.

## Implemented

- Positive Horn-clause fact/rule representation.
- Deterministic unification and conjunctive matching.
- Forward chaining to a fixed point with an explanation trace.
- Positive conjunctive FOL query endpoint.
- Live knowledge-base construction from roads, emergencies, ambulances,
  hospitals and shelters.
- `HighFailureProb(R) -> Unsafe(R) -> Avoid(R)` reasoning.
- Critical/high-priority emergency reasoning and facility candidate facts.
- A* route requests now consult the symbolic `Avoid(R)` conclusions as a soft
  penalty; blocked roads remain hard exclusions.
- `/api/ai/infer` and `/api/ai/fol`.
- AI Reasoning page with facts, derived facts, rule trace and FOL query UI.

## Design constraints

The engine intentionally excludes negation, function symbols and arbitrary
quantifier syntax. The project's needed FOL demonstration is a positive
conjunctive query over ground facts. Keeping the subset small makes the
inference trace inspectable and deterministic.

## Phase boundary

Phase 6 does **not** allocate ambulances or hospitals. It exposes candidate
facts for the CSP introduced in Phase 7. Phase 6 also does not implement
automatic replanning; that belongs to Phase 9.

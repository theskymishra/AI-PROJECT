# Phase 12 Findings — AI Decision Explainability & Audit Trail

## Objective
Provide a transparent, deterministic explanation of the current AI response pipeline so that a user can inspect why an emergency is assigned, planned, monitored, or flagged for allocation.

## Findings
- The explanation service is read-only and derives its report from the existing simulation state.
- Each active emergency receives a decision summary and a four-stage explanation when a complete assignment exists.
- CSP allocation is represented as the resource-decision stage.
- HTN planning is represented by the standard dispatch → load → transport → handoff decomposition already established in Phase 8.
- Monitoring contributes the current attention/recommendation state from Phase 11.
- The report also exposes the number of current timeline audit events and the current HTN plan status/length.

## Academic value
Phase 12 demonstrates explainable AI concepts through an explicit decision trace rather than an opaque single output. It connects the AI components already implemented in the project and gives the frontend a human-readable audit surface.

## Safety / scope
This remains an academic disaster-response simulation. It is not an operational emergency-management system and does not issue real-world dispatch decisions.

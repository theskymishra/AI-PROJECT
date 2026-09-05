# AI-DERS Phase 11 — Response Monitoring & Adaptive Replanning Assessment

Phase 11 builds directly on Phase 10 HTN plan execution.

## What it adds

- Read-only live response health assessment.
- Emergency-by-emergency monitoring.
- Resource capacity summary for ambulances and hospital beds.
- Detection of missing/invalid assignments.
- Replanning-readiness check using the existing Phase 8 HTN planner.
- Frontend monitoring dashboard with attention items and recommendations.

## Design rule

Phase 11 does **not** mutate simulation state. It observes the same in-memory `WorldState` used by Phases 1–10 and asks the existing planner for a fresh plan only when the user requests a replanning check.

## APIs

- `GET /api/ai/monitoring/status`
- `POST /api/ai/monitoring/replan-check`

## Intended flow

Simulation → CSP allocation → HTN planning → Phase 10 execution → **Phase 11 monitoring** → if invalidation is detected, run allocation/planning again.

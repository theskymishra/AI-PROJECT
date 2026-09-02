# AI-DERS Phase 8 — AI Response Planning

This is a **Phase 7 → Phase 8 overlay**, not a replacement project.

## What Phase 8 adds

- Deterministic Hierarchical Task Network (HTN) response planner.
- `POST /api/ai/plan` backend endpoint.
- Explicit planning actions with preconditions/add/delete effects.
- Hierarchical plan tree for explainability.
- Read-only Planning page at `/planning`.
- Unit and integration tests.
- Idempotent `scripts/apply_phase8.py` to wire the overlay into your existing Phase 7 checkout.

## Important

Phase 8 consumes **Phase 7 ambulance/hospital assignments**. It does not perform resource allocation and it does not mutate simulation state.

If there are no assigned, unresolved emergencies, the planner returns `NO_PLAN` rather than inventing a response.

## Apply

From the root of your `ai-ders` project, after copying this overlay into the project directory:

```bash
python3 scripts/apply_phase8.py
```

Then run the tests.

### Backend

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

### Frontend

```bash
cd frontend
npm run typecheck
npm test
npm run build
```

The planner is intentionally read-only, so previewing it is safe.

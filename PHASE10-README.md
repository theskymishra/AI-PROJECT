# AI-DERS Phase 10 — HTN Plan Execution

This is a **Phase 9 → Phase 10 overlay**, not a replacement project.

## What Phase 10 adds

- Explicit execution of the Phase 8 HTN response plan.
- A stepwise execution cursor so every primitive action can be demonstrated.
- Safe state transitions for `DISPATCH`, `LOAD_PATIENTS`, `TRANSPORT`, and `HANDOFF`.
- Execution validation against the current Phase 7 resource assignments.
- Stale-plan protection when assignments change.
- Timeline entries labelled `AI_EXECUTION`.
- SSE `plan` events carrying a fresh simulation snapshot after execution.
- `POST /api/ai/execution/prepare`.
- `POST /api/ai/execution/step`.
- `POST /api/ai/execution/all`.
- `POST /api/ai/execution/reset`.
- Execution Control page at `/execution`.
- Unit and integration tests.
- Idempotent `scripts/apply_phase10.py`.

## Important integration rule

Phase 7 already reserves hospital beds when an allocation is applied. Phase 10 therefore **does not decrement hospital beds again during handoff**. The execution layer changes operational status while preserving the resource accounting established by the CSP allocator.

Phase 7 also marks an allocated ambulance as `DISPATCHED`. The first HTN primitive is therefore treated as the transition from an allocated dispatch state to `EN_ROUTE`, rather than requiring the ambulance to become available a second time.

## Demonstration flow

1. Start a scenario such as Moderate Flood or Severe Flood.
2. Advance until emergencies are created.
3. Open **Resources** and apply a CSP allocation.
4. Open **AI Planning** and confirm a `FOUND` plan.
5. Open **Plan Execution**.
6. Click **Prepare execution plan**.
7. Click **Execute next action** repeatedly to demonstrate each HTN primitive.
8. Watch ambulance/emergency status changes and the dashboard statistics update.
9. Alternatively use **Execute all remaining** to complete the response in one operation.

## Backend

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

## Frontend

```bash
cd ../frontend
npm run typecheck
npm test
npm run build
```

The feature remains an **academic simulation**. It is not an operational emergency-management system.

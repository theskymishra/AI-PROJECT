# AI-DERS — Phase 12 Overlay

## Phase 12: AI Decision Explainability & Audit Trail

This overlay is designed to be applied **on top of the verified Phase 11 codebase**.

### Purpose
Phase 12 makes the AI decision pipeline explainable without changing simulation state. It exposes a deterministic audit-style view of how the current emergency response moves through:

1. Sensing / inference
2. CSP resource allocation
3. HTN planning
4. HTN execution
5. Response monitoring

### Backend
- `backend/app/models/explainability.py`
- `backend/app/services/explainability_service.py`
- `backend/app/api/explainability.py`
- unit and integration tests

Endpoint:
- `GET /api/ai/explainability/report`

### Frontend
- `frontend/src/pages/ExplainabilityPage.tsx`
- Route: `/explainability`

### Integration
Run from the repository root:

```bash
python3 scripts/apply_phase12.py
```

The script is idempotent and wires the Phase 12 API, types, page, and navigation into the Phase 11 application.

### Design constraints
- Read-only: no simulation mutation.
- Local deterministic simulation only.
- No external AI APIs, database, Docker, or GPU.
- Existing Phase 1–11 contracts are preserved.

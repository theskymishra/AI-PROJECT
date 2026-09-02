# AI-DERS Phase 9 — Dempster-Shafer Evidence Fusion

This is a **Phase 8 → Phase 9 overlay**, not a replacement project.

## What Phase 9 adds

- Dempster-Shafer Theory (DST) evidence fusion over the existing noisy sensor observations.
- Set-valued evidence masses that explicitly preserve ignorance using the full frame `THETA`.
- Dempster's normalized combination rule and conflict measurement.
- Belief and plausibility intervals for each flood state.
- Pignistic probabilities as a decision-oriented distribution.
- `POST /api/ai/evidence` backend endpoint.
- Evidence Fusion page at `/evidence`.
- Unit and integration tests.
- Idempotent `scripts/apply_phase9.py`.

## Why Phase 9

Phase 5 already uses HMM + Bayesian inference. Phase 9 adds a distinct uncertainty model rather than duplicating Bayesian probabilities. DST can represent partial evidence such as `{HIGH, CRITICAL}` and keep residual mass on `THETA` (ignorance) instead of forcing one exact hypothesis.

The feature is **read-only**. It analyzes the current simulation sensors and never mutates simulation state.

## Apply

From the parent directory of `ai-ders`:

```bash
rsync -av AI-DERS-PHASE9-OVERLAY/ ai-ders/
```

Then:

```bash
cd ai-ders
python3 scripts/apply_phase9.py
```

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

Do not push yet; commit locally on `Local-setup` after all checks pass.

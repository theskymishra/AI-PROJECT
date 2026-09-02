# AI-DERS Phase 7 — rsync overlay

This package is a **Phase 6 → Phase 7 overlay**. It preserves the existing project structure.
It contains only files that are new or modified for Phase 7.

## Recommended Mac/Linux resync

1. Extract this folder so that `AI-DERS-PHASE7-RESYNC/` is beside your main project folder.
2. From the parent directory, run:

```bash
rsync -av AI-DERS-PHASE7-RESYNC/ AI-PROJECT/
```

Replace `AI-PROJECT/` with the actual path of your main AI-DERS checkout.

## Windows PowerShell

If `rsync` is available:

```powershell
rsync -av AI-DERS-PHASE7-RESYNC/ AI-PROJECT/
```

Otherwise, copy/merge the folders into the project root; do not delete existing Phase 6 files.

## What Phase 7 adds

- CSP emergency resource allocation service using MRV, backtracking and forward checking.
- `POST /api/ai/allocate` preview/apply endpoint.
- Phase 7 Resources UI at `/resources`.
- Frontend API/type/route integration.
- Unit and integration tests.
- Phase 7 documentation.

## Important

The overlay assumes your main project is the complete Phase 6 checkout. The uploaded Phase 6 patch is itself a patch, so it is **not** intended to replace the whole main project.

After resync:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Then:

```bash
cd ../frontend
npm run typecheck
npm test
npm run build
```

And from the project root:

```bash
node scripts/verify_contract.mjs
```

If you use the included idempotent script instead of copying the modified existing files:

```bash
python3 scripts/apply_phase7.py
```

The included script is optional; the overlay itself already contains the Phase 7 modifications.

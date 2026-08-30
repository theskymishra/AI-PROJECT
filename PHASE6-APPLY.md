# AI-DERS Phase 6 patch

Baseline: the Phase 5-complete `AI-DERS` project supplied for this task.

Copy these files into the matching paths of your existing Phase 5 project.
Do not copy `.git`, `.venv`, `node_modules`, `dist`, or Python cache files.

Phase 6 adds the symbolic knowledge engine, forward chaining, positive
conjunctive FOL queries, live risk-to-symbolic facts, the `Avoid(R)` routing
soft penalty, `/api/ai/infer`, `/api/ai/fol`, the AI Reasoning page, tests,
and Phase 6 documentation/build markers.

Verification performed in the build environment:

- Phase 6 backend unit/API tests: 7/7 passed.
- Backend non-async tests: 434/434 passed. The remaining 10 existing SSE async
  tests require the repository's async pytest configuration/plugin, which is
  available in the user's normal Phase 5 environment but not in this build
  container invocation.
- Live API contract harness: **111 passed, 0 failed**.
- Phase 5 integration/demo tests continued to pass.
- Frontend dependencies could not be fully installed in the build container,
  so run `npm run typecheck`, `npm test`, and `npm run build` on the Mac after
  applying the patch.

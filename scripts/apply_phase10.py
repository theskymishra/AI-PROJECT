"""Idempotently wire the Phase 10 HTN plan-execution overlay into Phase 9."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1))


main = PROJECT / "backend/app/main.py"
replace_once(main, "    evidence,\n    disaster,", "    evidence,\n    execution,\n    disaster,")
replace_once(
    main,
    '    app.include_router(evidence.router, prefix=settings.api_prefix)\n',
    '    app.include_router(evidence.router, prefix=settings.api_prefix)\n    app.include_router(execution.router, prefix=settings.api_prefix)\n',
)

api = PROJECT / "frontend/src/services/api.ts"
replace_once(
    api,
    'import type { EvidenceResult, HealthResponse, PlanResult } from "@/types";',
    'import type { EvidenceResult, ExecutionResult, HealthResponse, PlanResult } from "@/types";',
)
needle = '''export async function requestEvidence(maxSources = 8): Promise<EvidenceResult> {
  const { data } = await api.post<EvidenceResult>("/api/ai/evidence", { max_sources: maxSources });
  return data;
}
'''
addition = needle + '''
/* ========================================================================
   Phase 10 -- HTN plan execution
   ======================================================================== */

export async function prepareExecution(): Promise<ExecutionResult> {
  const { data } = await api.post<ExecutionResult>("/api/ai/execution/prepare");
  return data;
}

export async function executeNextAction(): Promise<ExecutionResult> {
  const { data } = await api.post<ExecutionResult>("/api/ai/execution/step");
  return data;
}

export async function executeAll(): Promise<ExecutionResult> {
  const { data } = await api.post<ExecutionResult>("/api/ai/execution/all");
  return data;
}

export async function resetExecution(): Promise<ExecutionResult> {
  const { data } = await api.post<ExecutionResult>("/api/ai/execution/reset");
  return data;
}
'''
replace_once(api, needle, addition)

types = PROJECT / "frontend/src/types/index.ts"
if "export interface ExecutionResult" not in types.read_text():
    with types.open("a") as f:
        f.write('''

/* ==========================================================================
   Phase 10 -- HTN plan execution contracts
   ========================================================================== */

export interface ExecutionSnapshot {
  stats: Record<string, number>;
  emergencies: Array<{
    id: EmergencyId;
    status: EmergencyStatus;
    assigned_ambulance?: AmbulanceId | null;
    assigned_hospital?: HospitalId | null;
  }>;
  ambulances: Array<{
    id: AmbulanceId;
    status: AmbulanceStatus;
    assigned_emergency?: EmergencyId | null;
  }>;
  hospitals: Array<{
    id: HospitalId;
    available_beds: number;
    total_beds: number;
  }>;
}

export interface ExecutionResult {
  status: string;
  message: string;
  plan: PlanAction[];
  next_action_index: number | null;
  executed_count: number;
  total_actions: number;
  last_action: PlanAction | null;
  tick: number;
  snapshot: ExecutionSnapshot;
}
''')

app = PROJECT / "frontend/src/App.tsx"
replace_once(app, 'import { EvidencePage } from "@/pages/EvidencePage";\n', 'import { EvidencePage } from "@/pages/EvidencePage";\nimport { ExecutionPage } from "@/pages/ExecutionPage";\n')
replace_once(app, '        <Route path="evidence" element={<EvidencePage />} />\n', '        <Route path="evidence" element={<EvidencePage />} />\n        <Route path="execution" element={<ExecutionPage />} />\n')

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(
    routes,
    'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, Route } from "lucide-react";',
    'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route } from "lucide-react";',
)
replace_once(
    routes,
    '  { path: "/evidence", label: "Evidence Fusion", icon: FlaskConical, phase: 9 },\n',
    '  { path: "/evidence", label: "Evidence Fusion", icon: FlaskConical, phase: 9 },\n  { path: "/execution", label: "Plan Execution", icon: PlayCircle, phase: 10 },\n',
)

print("Phase 10 edits applied successfully.")

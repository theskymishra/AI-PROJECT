"""Idempotently wire the Phase 11 monitoring overlay into Phase 10."""
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
replace_once(main, "    execution,\n    disaster,", "    execution,\n    monitoring,\n    disaster,")
replace_once(
    main,
    '    app.include_router(execution.router, prefix=settings.api_prefix)\n',
    '    app.include_router(execution.router, prefix=settings.api_prefix)\n    app.include_router(monitoring.router, prefix=settings.api_prefix)\n',
)

api = PROJECT / "frontend/src/services/api.ts"
replace_once(
    api,
    'import type { EvidenceResult, ExecutionResult, HealthResponse, PlanResult } from "@/types";',
    'import type { EvidenceResult, ExecutionResult, HealthResponse, MonitoringResult, PlanResult } from "@/types";',
)
needle = '''export async function resetExecution(): Promise<ExecutionResult> {
  const { data } = await api.post<ExecutionResult>("/api/ai/execution/reset");
  return data;
}
'''
addition = needle + '''
/* ========================================================================
   Phase 11 -- response monitoring
   ======================================================================== */

export async function getMonitoringStatus(): Promise<MonitoringResult> {
  const { data } = await api.get<MonitoringResult>("/api/ai/monitoring/status");
  return data;
}

export async function getReplanCheck(): Promise<MonitoringResult> {
  const { data } = await api.post<MonitoringResult>("/api/ai/monitoring/replan-check");
  return data;
}
'''
replace_once(api, needle, addition)

types = PROJECT / "frontend/src/types/index.ts"
if "export interface MonitoringResult" not in types.read_text():
    with types.open("a") as f:
        f.write('''

/* ==========================================================================
   Phase 11 -- response monitoring contracts
   ========================================================================== */

export interface MonitoringItem {
  emergency_id: EmergencyId;
  status: string;
  ambulance_id: AmbulanceId | null;
  hospital_id: HospitalId | null;
  severity: string | null;
  patients: number;
  route_ready: boolean;
  attention: string;
  recommendation: string;
}

export interface ResourceHealth {
  ambulances_available: number;
  ambulances_total: number;
  beds_available: number;
  beds_total: number;
  active_emergencies: number;
  assigned_emergencies: number;
}

export interface MonitoringResult {
  status: string;
  tick: number;
  overall: string;
  summary: string;
  health: ResourceHealth;
  items: MonitoringItem[];
  alerts: string[];
  recommendations: string[];
  replanning_required: boolean;
  plan_length: number;
  plan_status: string;
}
''')

app = PROJECT / "frontend/src/App.tsx"
replace_once(app, 'import { ExecutionPage } from "@/pages/ExecutionPage";\n', 'import { ExecutionPage } from "@/pages/ExecutionPage";\nimport { MonitoringPage } from "@/pages/MonitoringPage";\n')
replace_once(app, '        <Route path="execution" element={<ExecutionPage />} />\n', '        <Route path="execution" element={<ExecutionPage />} />\n        <Route path="monitoring" element={<MonitoringPage />} />\n')

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(
    routes,
    'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route } from "lucide-react";',
    'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route, ShieldCheck } from "lucide-react";',
)
replace_once(
    routes,
    '  { path: "/execution", label: "Plan Execution", icon: PlayCircle, phase: 10 },\n',
    '  { path: "/execution", label: "Plan Execution", icon: PlayCircle, phase: 10 },\n  { path: "/monitoring", label: "Response Monitoring", icon: ShieldCheck, phase: 11 },\n',
)

print("Phase 11 edits applied successfully.")

"""Idempotently wire Phase 12 explainability into the Phase 11 project."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1))

main = PROJECT / "backend/app/main.py"
replace_once(main, "    monitoring,\n    disaster,", "    monitoring,\n    explainability,\n    disaster,")
replace_once(main, '    app.include_router(monitoring.router, prefix=settings.api_prefix)\n', '    app.include_router(monitoring.router, prefix=settings.api_prefix)\n    app.include_router(explainability.router, prefix=settings.api_prefix)\n')

api = PROJECT / "frontend/src/services/api.ts"
replace_once(api, 'import type { EvidenceResult, ExecutionResult, HealthResponse, MonitoringResult, PlanResult } from "@/types";', 'import type { EvidenceResult, ExecutionResult, ExplainabilityResult, HealthResponse, MonitoringResult, PlanResult } from "@/types";')
needle = '''export async function getReplanCheck(): Promise<MonitoringResult> {
  const { data } = await api.post<MonitoringResult>("/api/ai/monitoring/replan-check");
  return data;
}
'''
replace_once(api, needle, needle + '''\n/* ========================================================================\n   Phase 12 -- decision explainability\n   ======================================================================== */\n\nexport async function getExplainabilityReport(): Promise<ExplainabilityResult> {\n  const { data } = await api.get<ExplainabilityResult>("/api/ai/explainability/report");\n  return data;\n}\n''')

types = PROJECT / "frontend/src/types/index.ts"
if "export interface ExplainabilityResult" not in types.read_text():
    with types.open("a") as f:
        f.write('''\n\n/* ==========================================================================\n   Phase 12 -- decision explainability contracts\n   ========================================================================== */\n\nexport interface DecisionStep {\n  component: string;\n  decision: string;\n  rationale: string;\n  evidence: string[];\n}\n\nexport interface EmergencyExplanation {\n  emergency_id: EmergencyId;\n  status: string;\n  severity: string | null;\n  patients: number;\n  ambulance_id: AmbulanceId | null;\n  hospital_id: HospitalId | null;\n  decision: string;\n  rationale: string;\n  steps: DecisionStep[];\n}\n\nexport interface ExplainabilityResult {\n  status: string;\n  tick: number;\n  summary: string;\n  ai_chain: string[];\n  explanations: EmergencyExplanation[];\n  audit_events: number;\n  plan_status: string;\n  plan_length: number;\n}\n''')

app = PROJECT / "frontend/src/App.tsx"
replace_once(app, 'import { MonitoringPage } from "@/pages/MonitoringPage";\n', 'import { MonitoringPage } from "@/pages/MonitoringPage";\nimport { ExplainabilityPage } from "@/pages/ExplainabilityPage";\n')
replace_once(app, '        <Route path="monitoring" element={<MonitoringPage />} />\n', '        <Route path="monitoring" element={<MonitoringPage />} />\n        <Route path="explainability" element={<ExplainabilityPage />} />\n')

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(routes, 'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route, ShieldCheck } from "lucide-react";', 'import { Activity, Brain, Boxes, BrainCircuit, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route, ShieldCheck } from "lucide-react";')
replace_once(routes, '  { path: "/monitoring", label: "Response Monitoring", icon: ShieldCheck, phase: 11 },\n', '  { path: "/monitoring", label: "Response Monitoring", icon: ShieldCheck, phase: 11 },\n  { path: "/explainability", label: "AI Explainability", icon: BrainCircuit, phase: 12 },\n')

print("Phase 12 edits applied successfully.")

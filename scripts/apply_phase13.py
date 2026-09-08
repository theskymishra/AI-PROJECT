"""Idempotently wire Phase 13 response evaluation into the Phase 12 project."""
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
replace_once(main, "    explainability,\n    disaster,", "    explainability,\n    evaluation,\n    disaster,")
replace_once(main, '    app.include_router(explainability.router, prefix=settings.api_prefix)\n', '    app.include_router(explainability.router, prefix=settings.api_prefix)\n    app.include_router(evaluation.router, prefix=settings.api_prefix)\n')

api = PROJECT / "frontend/src/services/api.ts"
needle = '''export async function getExplainabilityReport(): Promise<ExplainabilityResult> {
  const { data } = await api.get<ExplainabilityResult>("/api/ai/explainability/report");
  return data;
}
'''
replace_once(api, needle, needle + '''\n/* ========================================================================\n   Phase 13 -- response evaluation\n   ======================================================================== */\n\nexport async function getEvaluationReport(): Promise<EvaluationResult> {\n  const { data } = await api.get<EvaluationResult>("/api/ai/evaluation/report");\n  return data;\n}\n''')
replace_once(api, 'ExplainabilityResult, HealthResponse, MonitoringResult, PlanResult', 'EvaluationResult, ExplainabilityResult, HealthResponse, MonitoringResult, PlanResult')

types = PROJECT / "frontend/src/types/index.ts"
if "export interface EvaluationMetric" not in types.read_text():
    types.open("a").write('''\n\n/* ==========================================================================\n   Phase 13 -- response evaluation contracts\n   ========================================================================== */\n\nexport interface EvaluationMetric {\n  name: string;\n  value: number;\n  unit: string;\n  interpretation: string;\n}\n\nexport interface EvaluationResult {\n  status: string;\n  tick: number;\n  scenario: string;\n  summary: string;\n  readiness: string;\n  metrics: EvaluationMetric[];\n  recommendations: string[];\n  active_emergencies: number;\n  resolved_emergencies: number;\n  unresolvable_emergencies: number;\n  assigned_emergencies: number;\n  unassigned_emergencies: number;\n  ambulances_available: number;\n  ambulances_total: number;\n  beds_available: number;\n  beds_total: number;\n  audit_events: number;\n  plan_status: string;\n  plan_length: number;\n}\n''')

app = PROJECT / "frontend/src/App.tsx"
replace_once(app, 'import { ExplainabilityPage } from "@/pages/ExplainabilityPage";\n', 'import { ExplainabilityPage } from "@/pages/ExplainabilityPage";\nimport { EvaluationPage } from "@/pages/EvaluationPage";\n')
replace_once(app, '        <Route path="explainability" element={<ExplainabilityPage />} />\n', '        <Route path="explainability" element={<ExplainabilityPage />} />\n        <Route path="evaluation" element={<EvaluationPage />} />\n')

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(routes, 'import { Activity, Brain, Boxes, BrainCircuit, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route, ShieldCheck } from "lucide-react";', 'import { Activity, BarChart3, Brain, Boxes, BrainCircuit, FlaskConical, GitBranch, LayoutDashboard, Map, PlayCircle, Route, ShieldCheck } from "lucide-react";')
replace_once(routes, '  { path: "/explainability", label: "AI Explainability", icon: BrainCircuit, phase: 12 },\n', '  { path: "/explainability", label: "AI Explainability", icon: BrainCircuit, phase: 12 },\n  { path: "/evaluation", label: "Response Evaluation", icon: BarChart3, phase: 13 },\n')

print("Phase 13 edits applied successfully.")

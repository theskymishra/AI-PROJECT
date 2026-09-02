"""Idempotently wire the Phase 9 Dempster-Shafer overlay into Phase 8."""
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
replace_once(main, "    planning,\n    disaster,", "    planning,\n    evidence,\n    disaster,")
replace_once(main, '    app.include_router(planning.router, prefix=settings.api_prefix)\n', '    app.include_router(planning.router, prefix=settings.api_prefix)\n    app.include_router(evidence.router, prefix=settings.api_prefix)\n')

api = PROJECT / "frontend/src/services/api.ts"
replace_once(api, 'import type { HealthResponse } from "@/types";', 'import type { EvidenceResult, HealthResponse, PlanResult } from "@/types";')
needle = 'export async function requestPlanning(): Promise<PlanResult> {\n  const { data } = await api.post<PlanResult>("/api/ai/plan");\n  return data;\n}\n'
addition = needle + '''\n/* ========================================================================\n   Phase 9 -- Dempster-Shafer evidence fusion\n   ======================================================================== */\n\nexport async function requestEvidence(maxSources = 8): Promise<EvidenceResult> {\n  const { data } = await api.post<EvidenceResult>("/api/ai/evidence", { max_sources: maxSources });\n  return data;\n}\n'''
replace_once(api, needle, addition)

# Phase 9 contracts are appended so no existing frozen type ordering is disturbed.
types = PROJECT / "frontend/src/types/index.ts"
if "export interface EvidenceSource" not in types.read_text():
    with types.open("a") as f:
        f.write('''\n\n/* ==========================================================================\n   Phase 9 -- Dempster-Shafer evidence fusion contracts\n   ========================================================================== */\n\nexport interface EvidenceRequest {\n  max_sources?: number;\n}\n\nexport interface EvidenceSource {\n  source_id: SensorId;\n  tick: number;\n  observation: Observation;\n  reliability: number;\n  masses: Record<string, number>;\n}\n\nexport interface EvidenceResult {\n  status: string;\n  frame: string[];\n  sources: EvidenceSource[];\n  combined_masses: Record<string, number>;\n  belief: Record<string, number>;\n  plausibility: Record<string, number>;\n  pignistic: Record<string, number>;\n  conflict: number;\n  evidence_count: number;\n  execution_ms: number;\n}\n''')

app = PROJECT / "frontend/src/App.tsx"
replace_once(app, 'import { PlanningPage } from "@/pages/PlanningPage";\n', 'import { PlanningPage } from "@/pages/PlanningPage";\nimport { EvidencePage } from "@/pages/EvidencePage";\n')
replace_once(app, '        <Route path="planning" element={<PlanningPage />} />\n', '        <Route path="planning" element={<PlanningPage />} />\n        <Route path="evidence" element={<EvidencePage />} />\n')

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(routes, 'import { Activity, Brain, Boxes, GitBranch, LayoutDashboard, Map, Route } from "lucide-react";', 'import { Activity, Brain, Boxes, FlaskConical, GitBranch, LayoutDashboard, Map, Route } from "lucide-react";')
replace_once(routes, '  { path: "/resources", label: "Resources", icon: Boxes, phase: 7 },\n  { path: "/planning", label: "AI Planning", icon: GitBranch, phase: 8 },\n', '  { path: "/resources", label: "Resources", icon: Boxes, phase: 7 },\n  { path: "/planning", label: "AI Planning", icon: GitBranch, phase: 8 },\n  { path: "/evidence", label: "Evidence Fusion", icon: FlaskConical, phase: 9 },\n')

print("Phase 9 edits applied successfully.")

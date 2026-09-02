"""Idempotently wire the Phase 8 overlay into a Phase 7 checkout."""
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
replace_once(
    main,
    "    allocation,\n    disaster,",
    "    allocation,\n    planning,\n    disaster,",
)
replace_once(
    main,
    '    app.include_router(allocation.router, prefix=settings.api_prefix)\n',
    '    app.include_router(allocation.router, prefix=settings.api_prefix)\n    app.include_router(planning.router, prefix=settings.api_prefix)\n',
)

api = PROJECT / "frontend/src/services/api.ts"
needle = 'export async function requestAllocation(\n  request: AllocationRequest = {},\n): Promise<CSPResult> {\n  const { data } = await api.post<CSPResult>("/api/ai/allocate", request);\n  return data;\n}\n'
addition = needle + '\n/* ========================================================================\n   Phase 8 -- HTN response planning\n   ======================================================================== */\nimport type { PlanResult } from "@/types";\n\nexport async function requestPlanning(): Promise<PlanResult> {\n  const { data } = await api.post<PlanResult>("/api/ai/plan");\n  return data;\n}\n'
replace_once(api, needle, addition)

app = PROJECT / "frontend/src/App.tsx"
replace_once(
    app,
    'import { ResourcesPage } from "@/pages/ResourcesPage";\n',
    'import { ResourcesPage } from "@/pages/ResourcesPage";\nimport { PlanningPage } from "@/pages/PlanningPage";\n',
)
replace_once(
    app,
    '        <Route path="resources" element={<ResourcesPage />} />\n',
    '        <Route path="resources" element={<ResourcesPage />} />\n        <Route path="planning" element={<PlanningPage />} />\n',
)

routes = PROJECT / "frontend/src/components/layout/routes.ts"
replace_once(
    routes,
    'import { Activity, Brain, Boxes, LayoutDashboard, Map, Route } from "lucide-react";',
    'import { Activity, Brain, Boxes, GitBranch, LayoutDashboard, Map, Route } from "lucide-react";',
)
replace_once(
    routes,
    '  { path: "/resources", label: "Resources", icon: Boxes, phase: 7 },\n',
    '  { path: "/resources", label: "Resources", icon: Boxes, phase: 7 },\n  { path: "/planning", label: "AI Planning", icon: GitBranch, phase: 8 },\n',
)

print("Phase 8 edits applied successfully.")

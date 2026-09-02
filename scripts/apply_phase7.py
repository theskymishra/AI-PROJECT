"""Idempotently apply the Phase 7 edits to an existing AI-DERS Phase 6 tree."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Could not find expected Phase 6 text in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + block.strip() + "\n", encoding="utf-8")


def main() -> None:
    config = ROOT / "backend/app/config.py"
    replace_once(config, "CURRENT_PHASE = 6", "CURRENT_PHASE = 7")

    main_py = ROOT / "backend/app/main.py"
    replace_once(
        main_py,
        "    ai,\n    disaster,",
        "    ai,\n    allocation,\n    disaster,",
    )
    replace_once(
        main_py,
        "    app.include_router(ai.router, prefix=settings.api_prefix)\n",
        "    app.include_router(ai.router, prefix=settings.api_prefix)\n    app.include_router(allocation.router, prefix=settings.api_prefix)\n",
    )

    types = ROOT / "frontend/src/types/index.ts"
    append_once(
        types,
        "export interface AllocationRequest",
        '''/* ========================================================================\n   Phase 7 -- resource allocation request\n   ======================================================================== */\nexport interface AllocationRequest {\n  /** Preview by default. Set true to commit assignments to live state. */\n  apply?: boolean;\n}''',
    )

    api = ROOT / "frontend/src/services/api.ts"
    append_once(
        api,
        "requestAllocation",
        '''/* ========================================================================\n   Phase 7 -- CSP resource allocation\n   ======================================================================== */\nimport type { AllocationRequest, CSPResult } from "@/types";\n\nexport async function requestAllocation(\n  request: AllocationRequest = {},\n): Promise<CSPResult> {\n  const { data } = await api.post<CSPResult>("/api/ai/allocate", request);\n  return data;\n}''',
    )

    routes = ROOT / "frontend/src/components/layout/routes.ts"
    replace_once(
        routes,
        'import { Activity, Brain, LayoutDashboard, Map, Route } from "lucide-react";',
        'import { Activity, Brain, Boxes, LayoutDashboard, Map, Route } from "lucide-react";',
    )
    replace_once(
        routes,
        '  { path: "/reasoning", label: "AI Reasoning", icon: Brain, phase: 6 },\n',
        '  { path: "/reasoning", label: "AI Reasoning", icon: Brain, phase: 6 },\n  { path: "/resources", label: "Resources", icon: Boxes, phase: 7 },\n',
    )

    app = ROOT / "frontend/src/App.tsx"
    replace_once(
        app,
        'import { ReasoningPage } from "@/pages/ReasoningPage";\n',
        'import { ReasoningPage } from "@/pages/ReasoningPage";\nimport { ResourcesPage } from "@/pages/ResourcesPage";\n',
    )
    replace_once(
        app,
        '        <Route path="reasoning" element={<ReasoningPage />} />\n',
        '        <Route path="reasoning" element={<ReasoningPage />} />\n        <Route path="resources" element={<ResourcesPage />} />\n',
    )

    print("Phase 7 edits applied successfully.")


if __name__ == "__main__":
    main()

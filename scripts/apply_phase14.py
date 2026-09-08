"""Phase 14 overlay marker.

The Phase 14 files are already present in the project. This script is intentionally
idempotent and only verifies that the final integration files exist.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "backend/app/models/final_report.py",
    ROOT / "backend/app/services/final_report_service.py",
    ROOT / "backend/app/api/final_report.py",
    ROOT / "frontend/src/pages/FinalReportPage.tsx",
    ROOT / "docs/PHASE-14-FINDINGS.md",
]

missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
if missing:
    raise SystemExit("Phase 14 files missing: " + ", ".join(missing))

print("AI-DERS Phase 14 final integration files are present.")

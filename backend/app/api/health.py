"""System health endpoint.

This is the only endpoint that exists in Phase 1. It is what the frontend uses
to prove end-to-end connectivity: browser -> Vite dev server -> CORS -> FastAPI.

It deliberately does NOT report simulation status. There is no simulation until
Phase 2, and a field reading "not_implemented" would be a placeholder.
"""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(tags=["system"])

_STARTED_AT = time.monotonic()


class HealthResponse(BaseModel):
    """Liveness and build information."""

    status: Literal["ok"] = Field(
        description="Always 'ok'. Failure is signalled by the connection failing, "
        "not by a different value here."
    )
    app: str = Field(description="Short application name.")
    full_name: str = Field(description="Expanded project name.")
    tagline: str = Field(description="Project tagline.")
    version: str = Field(description="Backend version.")
    phase: int = Field(description="Implementation phase this build corresponds to.")
    total_phases: int = Field(description="Total planned phases.")
    uptime_seconds: float = Field(
        description="Seconds since the backend process started."
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend liveness and build information",
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        full_name=settings.app_full_name,
        tagline=settings.app_tagline,
        version=settings.version,
        phase=settings.phase,
        total_phases=settings.total_phases,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
    )

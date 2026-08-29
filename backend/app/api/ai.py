"""AI endpoints.

Phase 4 adds routing. Later phases append allocation, inference, probabilistic
reasoning and planning to this router.

These endpoints run the REAL algorithm against the CURRENT simulation state --
they are not a separate demo path. The same RoutingService instance backs both
this endpoint and any internal caller, so an examiner poking at /api/ai/route
is exercising exactly the code the simulation uses.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.ai_result import RouteResult
from app.services.routing_service import routing_service
from app.simulation.engine import engine

router = APIRouter(tags=["ai"])


class RouteRequest(BaseModel):
    start: str = Field(description="Start node id, e.g. 'N1'.")
    goal: str = Field(description="Goal node id, e.g. 'N17'.")
    use_cache: bool = Field(
        default=True,
        description=(
            "Set false to force a fresh search. Used by the UI when it wants "
            "honest expansion metrics rather than a cached result's."
        ),
    )


class RouteResponse(BaseModel):
    route: RouteResult
    cache: dict[str, float | int]
    weights: dict[str, float]


@router.post(
    "/ai/route",
    response_model=RouteResponse,
    summary="Disaster-aware A* route between two nodes",
)
def post_route(request: RouteRequest) -> RouteResponse:
    try:
        route = routing_service.route(
            engine.state,
            request.start,
            request.goal,
            use_cache=request.use_cache,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc

    stats = routing_service.stats
    return RouteResponse(
        route=route,
        cache={
            "hits": stats.hits,
            "misses": stats.misses,
            "invalidations": stats.invalidations,
            "entries": stats.entries,
            "hit_rate": round(stats.hit_rate, 4),
        },
        weights={
            "flood": routing_service.alpha,
            "damage": routing_service.beta,
            "failure": routing_service.gamma,
        },
    )

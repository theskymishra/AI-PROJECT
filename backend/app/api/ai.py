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

from app.ai.probability import bayesian
from app.config import FLOOD_STATES
from app.ai.probability.hmm import filter_sequence
from app.models.ai_result import RouteResult
from app.services.risk_service import risk_service
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
        # Phase 6 symbolic reasoning derives Avoid(R) from HighFailureProb(R)
        # and Blocked(R). The routing service keeps this as a soft penalty; a
        # blocked road remains a hard exclusion in RoadGraph.
        knowledge = build_knowledge_base(engine.state)
        knowledge.infer()
        unsafe = frozenset(
            fact.args[0] for fact in knowledge.facts if fact.predicate == "Avoid"
        )
        route = routing_service.route(
            engine.state,
            request.start,
            request.goal,
            avoid=unsafe,
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


# ---------------------------------------------------------------------------
# Hidden Markov Model
# ---------------------------------------------------------------------------


class HMMRequest(BaseModel):
    observations: list[str] | None = Field(
        default=None,
        description=(
            "Optional observation sequence to filter from the prior. Omit to "
            "read the LIVE filter's current belief. Supplying a sequence runs "
            "a throwaway filter and never disturbs the live one."
        ),
    )


class HMMResponse(BaseModel):
    belief: dict[str, float]
    most_likely: str
    entropy: float = Field(description="Shannon entropy in bits, 0 to 2.")
    step_likelihood: float = Field(
        description="P(o_t | o_1..o_t-1). Sustained low values mean the model "
        "is being surprised."
    )
    observation_history: list[str]
    belief_history: list[list[float]] = Field(
        description="One row per tick, ordered as FLOOD_STATES."
    )
    states: list[str]
    live: bool = Field(description="True when reading the live filter.")
    execution_ms: float


@router.post(
    "/ai/hmm",
    response_model=HMMResponse,
    summary="Filtered belief over the hidden flood state",
)
def post_hmm(request: HMMRequest) -> HMMResponse:
    if request.observations:
        try:
            run = filter_sequence(request.observations)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return HMMResponse(
            belief=run.belief.distribution,
            most_likely=run.belief.most_likely,
            entropy=run.belief.entropy,
            step_likelihood=run.belief.step_likelihood,
            observation_history=list(request.observations),
            belief_history=run.belief_history,
            states=list(FLOOD_STATES),
            live=False,
            execution_ms=run.execution_ms,
        )

    hmm = risk_service.hmm
    current = hmm.current()
    return HMMResponse(
        belief=current.distribution,
        most_likely=current.most_likely,
        entropy=current.entropy,
        step_likelihood=current.step_likelihood,
        observation_history=list(hmm.observation_history),
        belief_history=[row[:] for row in hmm.belief_history],
        states=list(FLOOD_STATES),
        live=True,
        execution_ms=0.0,
    )


# ---------------------------------------------------------------------------
# Bayesian Network
# ---------------------------------------------------------------------------


class BayesianRequest(BaseModel):
    rainfall: str | None = Field(
        default=None, description="Clamp Rainfall to LOW/MED/HIGH. Omit for live."
    )
    water_level: str | None = Field(
        default=None, description="Clamp WaterLevel to LOW/MED/HIGH. Omit for live."
    )
    use_hmm: bool = Field(
        default=True,
        description=(
            "False detaches the HMM's virtual evidence, leaving the "
            "Rainfall -> WaterLevel -> FloodSeverity chain to speak for "
            "itself. This is what makes those edges inspectable rather than "
            "merely present."
        ),
    )


class BayesianResponse(BaseModel):
    flood_severity: dict[str, float]
    water_level: dict[str, float]
    rainfall: dict[str, float]
    per_road: dict[str, float]
    evidence: dict[str, str]
    used_hmm_virtual_evidence: bool
    execution_ms: float
    riskiest_roads: list[dict[str, float | str]]


_BAND_VALUES = {"LOW", "MED", "HIGH"}


@router.post(
    "/ai/bayesian",
    response_model=BayesianResponse,
    summary="Road failure probabilities from the Bayesian Network",
)
def post_bayesian(request: BayesianRequest) -> BayesianResponse:
    for name, value in (("rainfall", request.rainfall), ("water_level", request.water_level)):
        if value is not None and value not in _BAND_VALUES:
            raise HTTPException(
                status_code=422,
                detail=f"{name} must be one of {sorted(_BAND_VALUES)}, got {value!r}",
            )

    state = engine.state
    rainfall = request.rainfall or bayesian.discretise_rainfall(
        state.environment.rainfall_mm
    )
    water = request.water_level or bayesian.discretise_water_level(
        state.environment.water_level_m
    )

    roads = {
        road_id: (str(road.elevation_band), road.damage_level)
        for road_id, road in state.roads.items()
    }
    result = bayesian.infer(
        roads=roads,
        rainfall_evidence=rainfall,
        water_level_evidence=water,
        hmm_belief=risk_service.hmm.belief if request.use_hmm else None,
    )

    ranked = sorted(result.per_road.items(), key=lambda kv: -kv[1])[:5]
    riskiest = [
        {
            "road_id": road_id,
            "probability": round(probability, 4),
            "elevation_band": str(state.roads[road_id].elevation_band),
        }
        for road_id, probability in ranked
    ]

    return BayesianResponse(
        flood_severity=result.flood_severity,
        water_level=result.water_level,
        rainfall=result.rainfall,
        per_road=result.per_road,
        evidence={"Rainfall": rainfall, "WaterLevel": water},
        used_hmm_virtual_evidence=result.used_virtual_evidence,
        execution_ms=result.execution_ms,
        riskiest_roads=riskiest,
    )

# ---------------------------------------------------------------------------
# Phase 6 -- symbolic knowledge engine
# ---------------------------------------------------------------------------

from app.ai.knowledge.knowledge_base import build_knowledge_base
from app.ai.knowledge.parser import parse_atom, parse_conjunction
from app.models.ai_result import FOLResult, InferenceResult


class InferenceRequest(BaseModel):
    """Optional extra facts for a what-if inference run."""

    facts: list[str] = Field(default_factory=list, description="Facts such as HighFailureProb(R17).")


class FOLRequest(BaseModel):
    query: str = Field(description="Positive conjunctive query, e.g. Unsafe(R) or Unsafe(R) & Road(R).")


@router.post(
    "/ai/infer",
    response_model=InferenceResult,
    summary="Forward-chain the live symbolic knowledge base",
)
def post_infer(request: InferenceRequest) -> InferenceResult:
    kb = build_knowledge_base(engine.state)
    for raw in request.facts:
        try:
            kb.add_fact(parse_atom(raw))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return kb.infer()


@router.post(
    "/ai/fol",
    response_model=FOLResult,
    summary="Run a positive conjunctive first-order query",
)
def post_fol(request: FOLRequest) -> FOLResult:
    try:
        patterns = parse_conjunction(request.query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    kb = build_knowledge_base(engine.state)
    return kb.query(patterns)

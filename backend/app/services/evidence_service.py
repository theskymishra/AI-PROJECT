"""Phase 9 Dempster-Shafer evidence fusion for noisy disaster sensors.

The simulation already provides noisy categorical sensor observations. Phase 5
uses those observations in a Bayesian/HMM pipeline. Phase 9 adds a second,
independent uncertainty representation: Dempster-Shafer Theory (DST).

DST is useful here because a sensor may support a SET of flood states instead
of pretending to know the exact state. The remaining mass is assigned to the
full frame (ignorance). Independent sources are combined with Dempster's rule.
"""
from __future__ import annotations

from time import perf_counter
from typing import Iterable

from app.models.evidence import EvidenceResult, EvidenceSource
from app.simulation.state import WorldState

FRAME = ("NORMAL", "RISING", "HIGH", "CRITICAL")
THETA = frozenset(FRAME)

# Observation -> (supported subset, base support). The subset deliberately
# contains multiple states: this is where DST represents ambiguity/ignorance.
OBSERVATION_MASS: dict[str, tuple[frozenset[str], float]] = {
    "LOW_WATER": (frozenset({"NORMAL", "RISING"}), 0.75),
    "MEDIUM_WATER": (frozenset({"RISING", "HIGH"}), 0.75),
    "HIGH_WATER": (frozenset({"HIGH", "CRITICAL"}), 0.80),
    "RAPIDLY_RISING": (frozenset({"RISING", "HIGH", "CRITICAL"}), 0.85),
}


def _key(states: Iterable[str]) -> str:
    return "{" + ",".join(sorted(states, key=FRAME.index)) + "}"


def _parse_key(key: str) -> frozenset[str]:
    if key == "THETA":
        return THETA
    return frozenset(key.strip("{}").split(","))


def mass_for_observation(observation: str, reliability: float = 0.85) -> dict[str, float]:
    """Return a basic probability assignment (BPA) for one sensor reading."""
    if observation not in OBSERVATION_MASS:
        raise ValueError(f"unknown observation {observation!r}")
    if not 0.0 <= reliability <= 1.0:
        raise ValueError("reliability must be between 0 and 1")

    supported, support = OBSERVATION_MASS[observation]
    masses = {
        _key(supported): support * reliability,
        "THETA": 1.0 - support * reliability,
    }
    return {k: round(v, 10) for k, v in masses.items() if v > 0.0}


def combine_masses(left: dict[str, float], right: dict[str, float]) -> tuple[dict[str, float], float]:
    """Combine two BPAs using Dempster's normalized conjunctive rule."""
    combined: dict[frozenset[str], float] = {}
    conflict = 0.0
    for left_key, left_mass in left.items():
        left_set = _parse_key(left_key)
        for right_key, right_mass in right.items():
            right_set = _parse_key(right_key)
            intersection = left_set & right_set
            product = left_mass * right_mass
            if not intersection:
                conflict += product
            else:
                combined[intersection] = combined.get(intersection, 0.0) + product

    if conflict >= 1.0 - 1e-12:
        raise ValueError("total evidence conflict is 1.0; Dempster normalization is undefined")

    normalizer = 1.0 - conflict
    result = {
        ("THETA" if states == THETA else _key(states)): mass / normalizer
        for states, mass in combined.items()
    }
    return result, conflict


def belief_and_plausibility(masses: dict[str, float]) -> tuple[dict[str, float], dict[str, float]]:
    """Compute Bel(A) and Pl(A) for singleton flood-state hypotheses."""
    belief: dict[str, float] = {}
    plausibility: dict[str, float] = {}
    for state in FRAME:
        singleton = {state}
        belief[state] = round(sum(m for k, m in masses.items() if _parse_key(k) <= singleton), 10)
        plausibility[state] = round(sum(m for k, m in masses.items() if _parse_key(k) & singleton), 10)
    return belief, plausibility


def pignistic(masses: dict[str, float]) -> dict[str, float]:
    """Convert set-valued BPA into a decision distribution for display."""
    result = {state: 0.0 for state in FRAME}
    for key, mass in masses.items():
        states = _parse_key(key)
        if not states:
            continue
        share = mass / len(states)
        for state in states:
            result[state] += share
    return {state: round(value, 10) for state, value in result.items()}


class EvidenceFusionService:
    """Fuse the latest sensor readings without mutating simulation state."""

    def analyze(self, state: WorldState, max_sources: int = 8) -> EvidenceResult:
        started = perf_counter()
        readings = sorted(state.sensors.values(), key=lambda r: (-r.tick, r.sensor_id))[:max_sources]
        readings = sorted(readings, key=lambda r: r.sensor_id)

        sources: list[EvidenceSource] = []
        combined: dict[str, float] | None = None
        total_conflict = 0.0

        for reading in readings:
            reliability = 0.85
            masses = mass_for_observation(reading.observation.value, reliability)
            sources.append(
                EvidenceSource(
                    source_id=reading.sensor_id,
                    tick=reading.tick,
                    observation=reading.observation.value,
                    reliability=reliability,
                    masses=masses,
                )
            )
            if combined is None:
                combined = masses
            else:
                combined, conflict = combine_masses(combined, masses)
                total_conflict = 1.0 - (1.0 - total_conflict) * (1.0 - conflict)

        if combined is None:
            combined = {"THETA": 1.0}

        belief, plausibility = belief_and_plausibility(combined)
        decision = pignistic(combined)
        status = "FUSED" if sources else "NO_EVIDENCE"

        return EvidenceResult(
            status=status,
            frame=list(FRAME),
            sources=sources,
            combined_masses={k: round(v, 10) for k, v in combined.items()},
            belief=belief,
            plausibility=plausibility,
            pignistic=decision,
            conflict=round(total_conflict, 10),
            evidence_count=len(sources),
            execution_ms=round((perf_counter() - started) * 1000, 4),
        )


evidence_service = EvidenceFusionService()

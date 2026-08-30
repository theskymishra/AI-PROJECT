"""Risk service: sensors -> HMM -> Bayesian Network -> per-road P(failure).

THE PIPELINE LINK THIS PHASE EXISTS TO BUILD
--------------------------------------------
    noisy observation  ->  HMM filter  ->  virtual evidence
                                              |
    rainfall + water gauge (hard evidence) ----+--> Bayesian Network
                                                        |
                                          road.failure_probability
                                                        |
                                             A* gamma cost term
                                                        |
                                                 chosen route

That chain is the single most valuable thing in the project to demonstrate: it
connects Module 6 (probabilistic reasoning) to Module 2 (informed search) with
real numbers at every step and nothing hard-coded.

WHICH OBSERVATION FEEDS THE HMM
-------------------------------
SEN6, the river gauge. A hidden Markov model takes ONE observation per
timestep; fusing six zone sensors into a single symbol would require an
observation model this project does not have, and picking one canonical stream
is both standard and honest. The other five sensors still drive the display and
the zone flood levels.

ENVIRONMENT VERSION
-------------------
P(failure) moves a little every tick as water rises. Bumping
environment_version on every movement would invalidate the route cache
continuously and the cache would never serve a hit -- the exact bug
RISK_EPSILON exists to prevent. The version advances only when some road's
probability moves by at least RISK_EPSILON since the last bump.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.probability import bayesian
from app.ai.probability.hmm import FloodHMM, HMMBelief
from app.config import MAX_SENSOR_HISTORY, RISK_EPSILON

#: The river gauge. See the module docstring for why one stream, not six.
PRIMARY_SENSOR_ID = "SEN6"


@dataclass
class RiskSnapshot:
    """Everything the Risk page and the API need from one inference pass."""

    belief: dict[str, float]
    most_likely: str
    entropy: float
    step_likelihood: float
    observation: str
    flood_severity: dict[str, float]
    water_level_posterior: dict[str, float]
    rainfall_posterior: dict[str, float]
    rainfall_evidence: str
    water_level_evidence: str
    per_road: dict[str, float] = field(default_factory=dict)
    hmm_ms: float = 0.0
    bayes_ms: float = 0.0
    version_bumped: bool = False


class RiskService:
    """Owns the persistent HMM filter and runs the network each tick."""

    def __init__(self) -> None:
        self.hmm = FloodHMM()
        #: P(failure) as of the last environment_version bump. New values are
        #: compared against this, not against the previous tick, so a slow
        #: drift still triggers exactly one bump once it accumulates past the
        #: epsilon rather than never triggering at all.
        self._baseline: dict[str, float] = {}
        self.last: RiskSnapshot | None = None

    def reset(self) -> None:
        self.hmm.reset()
        self._baseline = {}
        self.last = None

    def observe(self, state) -> HMMBelief:
        """Advance the filter one tick using the river gauge."""
        sensor = state.sensors.get(PRIMARY_SENSOR_ID)
        if sensor is None:
            # Reachable only if the world drops the gauge. Holding the belief
            # steady is better than guessing an observation.
            return self.hmm.current()
        belief = self.hmm.update(str(sensor.observation))
        self.hmm.trim_history(MAX_SENSOR_HISTORY)
        return belief

    def assess(self, state, *, advance_filter: bool = True) -> RiskSnapshot:
        """Run the full chain and write P(failure) onto every road.

        Args:
            advance_filter: False re-runs the network against the CURRENT
                belief without consuming an observation. The API uses it so a
                what-if query cannot corrupt the live filter.
        """
        belief = self.observe(state) if advance_filter else self.hmm.current()

        environment = state.environment
        rainfall_evidence = bayesian.discretise_rainfall(environment.rainfall_mm)
        water_evidence = bayesian.discretise_water_level(environment.water_level_m)

        roads = {
            road_id: (str(road.elevation_band), road.damage_level)
            for road_id, road in state.roads.items()
        }

        result = bayesian.infer(
            roads=roads,
            rainfall_evidence=rainfall_evidence,
            water_level_evidence=water_evidence,
            hmm_belief=belief.distribution,
        )

        for road_id, probability in result.per_road.items():
            road = state.roads[road_id]
            road.failure_probability = round(probability, 6)
            # risk_score is display-only and never an input to A*. Keeping it
            # separate from failure_probability stops a presentation choice
            # leaking into the cost function.
            road.risk_score = round(
                min(1.0, 0.6 * probability + 0.4 * road.flood_level), 6
            )

        bumped = self._maybe_bump_version(state, result.per_road)

        snapshot = RiskSnapshot(
            belief=belief.distribution,
            most_likely=belief.most_likely,
            entropy=belief.entropy,
            step_likelihood=belief.step_likelihood,
            observation=(
                self.hmm.observation_history[-1]
                if self.hmm.observation_history
                else ""
            ),
            flood_severity=result.flood_severity,
            water_level_posterior=result.water_level,
            rainfall_posterior=result.rainfall,
            rainfall_evidence=rainfall_evidence,
            water_level_evidence=water_evidence,
            per_road=result.per_road,
            hmm_ms=0.0,
            bayes_ms=result.execution_ms,
            version_bumped=bumped,
        )
        self.last = snapshot
        return snapshot

    def _maybe_bump_version(self, state, per_road: dict[str, float]) -> bool:
        """Advance environment_version only past RISK_EPSILON."""
        if not self._baseline:
            self._baseline = dict(per_road)
            return False

        moved = any(
            abs(probability - self._baseline.get(road_id, 0.0)) >= RISK_EPSILON
            for road_id, probability in per_road.items()
        )
        if moved:
            state.environment_version += 1
            self._baseline = dict(per_road)
        return moved


#: Process-wide instance, mirroring the single-worker simulation engine.
risk_service = RiskService()

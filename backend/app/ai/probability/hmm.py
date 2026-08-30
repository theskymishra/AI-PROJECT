"""Hidden Markov Model over the flood state.

WHAT THIS DOES
--------------
The true flood state is hidden from the agent. Sensors emit a noisy symbol each
tick, drawn by the ENVIRONMENT from P(observation | true_state) -- the emission
matrix in config. This module runs the FORWARD ALGORITHM to recover a belief
distribution over the hidden state from that stream of symbols alone.

This is FILTERING: P(state_t | o_1 .. o_t). Not smoothing, not Viterbi. The
agent needs to act on what is true now, and the only quantity it needs is the
current belief. Viterbi would answer a different question (the single most
likely state SEQUENCE) that nothing downstream consumes.

    alpha_t(s) = P(o_t | s) * SUM_over_s' [ alpha_t-1(s') * A[s'][s] ]

with alpha normalised to sum to 1 after every step.

WHY NORMALISE EVERY STEP
------------------------
Two reasons. Unnormalised alpha values shrink geometrically -- after a few
hundred ticks they underflow to zero and the belief becomes 0/0. And the
normalised vector IS the filtered posterior, so it can be read straight out
without a second pass. The normalising constant is P(o_t | o_1..o_t-1), which
is retained as the per-step likelihood because a sustained low value means the
model is being surprised, and that is worth being able to see.

THE MODEL IS DELIBERATELY IMPERFECT
-----------------------------------
The transition matrix is the agent's approximation of how floods evolve. The
simulator derives the true state from water-level thresholds, which is a
different process. An HMM whose transition model exactly matched the generator
would be reading the answer off the environment rather than inferring it. The
resulting lag -- belief trailing truth by a few ticks, and genuine ambiguity
during transitions -- is the interesting behaviour, not a defect.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from app.config import (
    EMISSION_MATRIX,
    FLOOD_PRIOR,
    FLOOD_STATES,
    OBSERVATIONS,
    TRANSITION_MATRIX,
)


@dataclass
class HMMBelief:
    """Filtered posterior over the hidden flood state."""

    distribution: dict[str, float]
    most_likely: str
    #: P(o_t | o_1..o_t-1). Sustained low values mean the model is surprised.
    step_likelihood: float
    #: Shannon entropy in bits, 0 (certain) to 2 (uniform over four states).
    entropy: float
    observations_seen: int

    def probability(self, state: str) -> float:
        return self.distribution[state]


class FloodHMM:
    """Forward-algorithm filter over the flood state.

    Stateful across ticks: each observation updates the belief in place, which
    is what makes it a filter rather than a batch estimator. ``reset()``
    returns it to the prior.
    """

    def __init__(
        self,
        *,
        states: tuple[str, ...] = FLOOD_STATES,
        observations: tuple[str, ...] = OBSERVATIONS,
        transition: dict[str, dict[str, float]] | None = None,
        emission: dict[str, dict[str, float]] | None = None,
        prior: dict[str, float] | None = None,
    ) -> None:
        self.states = states
        self.observations = observations
        self.transition = transition or TRANSITION_MATRIX
        self.emission = emission or EMISSION_MATRIX
        self.prior = prior or FLOOD_PRIOR

        self._validate()

        self.belief: dict[str, float] = dict(self.prior)
        self.observation_history: list[str] = []
        self.belief_history: list[list[float]] = [
            [self.belief[s] for s in self.states]
        ]
        self.last_step_likelihood = 1.0

    # -- validation --------------------------------------------------------

    def _validate(self) -> None:
        """Fail at construction, not silently at inference time.

        A row that does not sum to 1 produces a belief that drifts away from a
        probability distribution over hundreds of ticks. The symptom appears
        far from the cause, so it is checked here.
        """
        for state in self.states:
            if state not in self.transition:
                raise ValueError(f"transition matrix is missing row {state!r}")
            if state not in self.emission:
                raise ValueError(f"emission matrix is missing row {state!r}")

            total = sum(self.transition[state].values())
            if not math.isclose(total, 1.0, abs_tol=1e-9):
                raise ValueError(
                    f"transition row {state!r} sums to {total}, not 1.0"
                )
            total = sum(self.emission[state].values())
            if not math.isclose(total, 1.0, abs_tol=1e-9):
                raise ValueError(f"emission row {state!r} sums to {total}, not 1.0")

        total = sum(self.prior.values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"prior sums to {total}, not 1.0")

    # -- filtering ---------------------------------------------------------

    def reset(self) -> None:
        self.belief = dict(self.prior)
        self.observation_history = []
        self.belief_history = [[self.belief[s] for s in self.states]]
        self.last_step_likelihood = 1.0

    def update(self, observation: str) -> HMMBelief:
        """Advance one tick with a single observation.

        Raises:
            ValueError: For a symbol outside the alphabet. Silently ignoring
                one would freeze the belief with no visible symptom.
        """
        if observation not in self.observations:
            raise ValueError(
                f"unknown observation {observation!r}; expected one of "
                f"{self.observations}"
            )

        # PREDICT: push the belief through the transition model.
        predicted = {
            nxt: sum(
                self.belief[cur] * self.transition[cur][nxt] for cur in self.states
            )
            for nxt in self.states
        }

        # UPDATE: weight by the likelihood of what was actually observed.
        weighted = {
            state: predicted[state] * self.emission[state][observation]
            for state in self.states
        }

        evidence = sum(weighted.values())
        if evidence <= 0.0:
            # Every state assigns zero probability to this observation. Not
            # reachable with the shipped matrices (no emission entry is 0), but
            # a custom matrix could do it, and dividing by zero here would
            # poison every later tick.
            raise ValueError(
                f"observation {observation!r} has zero likelihood under every "
                f"state; the emission matrix cannot explain this reading"
            )

        self.belief = {state: value / evidence for state, value in weighted.items()}
        self.last_step_likelihood = evidence
        self.observation_history.append(observation)
        self.belief_history.append([self.belief[s] for s in self.states])

        return self.current()

    def update_many(self, observations: list[str]) -> HMMBelief:
        """Filter a whole sequence. Used by the API for what-if queries."""
        result = self.current()
        for observation in observations:
            result = self.update(observation)
        return result

    def current(self) -> HMMBelief:
        return HMMBelief(
            distribution=dict(self.belief),
            most_likely=max(self.belief, key=lambda s: self.belief[s]),
            step_likelihood=self.last_step_likelihood,
            entropy=entropy_bits(self.belief),
            observations_seen=len(self.observation_history),
        )

    def trim_history(self, max_rows: int) -> None:
        """Bound retained history. This is a simulation, not a database."""
        if len(self.belief_history) > max_rows:
            self.belief_history = self.belief_history[-max_rows:]
        if len(self.observation_history) > max_rows:
            self.observation_history = self.observation_history[-max_rows:]


def entropy_bits(distribution: dict[str, float]) -> float:
    """Shannon entropy in bits.

    Used as the "how uncertain is the agent" readout. Zero when the belief has
    collapsed onto one state, 2.0 when it is uniform over four. A belief that
    sits at zero entropy every tick means the sensors are not actually noisy,
    which is the failure mode this whole design exists to avoid.
    """
    total = 0.0
    for probability in distribution.values():
        if probability > 0.0:
            total -= probability * math.log2(probability)
    return total


@dataclass
class HMMRun:
    """Result of filtering a sequence, with timing, for the API."""

    belief: HMMBelief
    execution_ms: float = 0.0
    belief_history: list[list[float]] = field(default_factory=list)


def filter_sequence(observations: list[str]) -> HMMRun:
    """Run the forward algorithm over a sequence from the prior.

    Stateless entry point for the API's what-if mode; the live pipeline uses a
    persistent FloodHMM instead.
    """
    started = time.perf_counter()
    hmm = FloodHMM()
    belief = hmm.update_many(observations)
    return HMMRun(
        belief=belief,
        execution_ms=round((time.perf_counter() - started) * 1000, 4),
        belief_history=[row[:] for row in hmm.belief_history],
    )

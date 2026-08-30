"""Hidden Markov Model forward algorithm.

The HMM must genuinely infer. A filter whose posterior pins at ~1.0 every tick
is not doing inference -- it is reading the answer -- and that is the failure
mode this whole design exists to avoid, so it is asserted directly.
"""

import math

import pytest

from app.ai.probability.hmm import FloodHMM, entropy_bits, filter_sequence
from app.config import FLOOD_PRIOR, FLOOD_STATES


@pytest.fixture
def hmm():
    return FloodHMM()


class TestConstruction:
    def test_starts_at_the_prior(self, hmm):
        assert hmm.belief == FLOOD_PRIOR

    def test_rejects_a_transition_row_that_does_not_normalise(self):
        broken = {s: {t: 0.1 for t in FLOOD_STATES} for s in FLOOD_STATES}
        with pytest.raises(ValueError, match="sums to"):
            FloodHMM(transition=broken)

    def test_rejects_a_missing_transition_row(self):
        partial = {"NORMAL": {s: 0.25 for s in FLOOD_STATES}}
        with pytest.raises(ValueError, match="missing row"):
            FloodHMM(transition=partial)

    def test_rejects_a_prior_that_does_not_normalise(self):
        with pytest.raises(ValueError, match="prior sums to"):
            FloodHMM(prior={s: 0.9 for s in FLOOD_STATES})


class TestFiltering:
    def test_belief_remains_a_probability_distribution(self, hmm):
        for observation in ["LOW_WATER", "HIGH_WATER", "RAPIDLY_RISING"] * 40:
            belief = hmm.update(observation)
            assert math.isclose(sum(belief.distribution.values()), 1.0, abs_tol=1e-9)
            assert all(0.0 <= p <= 1.0 for p in belief.distribution.values())

    def test_no_underflow_over_a_long_run(self, hmm):
        """Unnormalised alpha shrinks geometrically and dies. This is why the
        forward pass normalises every step."""
        for _ in range(2000):
            hmm.update("MEDIUM_WATER")
        assert math.isclose(sum(hmm.belief.values()), 1.0, abs_tol=1e-9)
        assert max(hmm.belief.values()) > 0.0

    def test_sustained_high_water_moves_belief_towards_severe_states(self, hmm):
        before = hmm.belief["NORMAL"]
        for _ in range(6):
            hmm.update("RAPIDLY_RISING")
        assert hmm.belief["NORMAL"] < before
        assert hmm.belief["CRITICAL"] > hmm.belief["NORMAL"]

    def test_sustained_low_water_keeps_belief_calm(self, hmm):
        for _ in range(10):
            hmm.update("LOW_WATER")
        assert hmm.current().most_likely == "NORMAL"

    def test_belief_recovers_when_conditions_ease(self, hmm):
        for _ in range(8):
            hmm.update("RAPIDLY_RISING")
        peak = hmm.belief["CRITICAL"]
        for _ in range(25):
            hmm.update("LOW_WATER")
        assert hmm.belief["CRITICAL"] < peak
        assert hmm.current().most_likely == "NORMAL"

    def test_the_posterior_does_not_collapse_to_certainty(self, hmm):
        """THE test that matters.

        Overlapping emission rows mean one observation can never identify the
        state. A filter reporting ~100% confidence would look hard-coded, and
        would mean the sensors are not actually noisy.
        """
        for observation in ["HIGH_WATER", "RAPIDLY_RISING", "MEDIUM_WATER"] * 10:
            belief = hmm.update(observation)
            assert max(belief.distribution.values()) < 0.99, (
                "the posterior collapsed; the emission model is not noisy"
            )
            assert belief.entropy > 0.05

    def test_a_single_observation_cannot_identify_the_state(self, hmm):
        belief = hmm.update("RAPIDLY_RISING")
        plausible = [p for p in belief.distribution.values() if p > 0.05]
        assert len(plausible) >= 2

    def test_belief_lags_a_sudden_change(self, hmm):
        """Filtering lag is the interesting behaviour, not a defect."""
        for _ in range(10):
            hmm.update("LOW_WATER")
        first = hmm.update("RAPIDLY_RISING")
        assert first.most_likely != "CRITICAL", "belief jumped instantly; no lag"
        for _ in range(4):
            later = hmm.update("RAPIDLY_RISING")
        assert later.most_likely in {"HIGH", "CRITICAL"}


class TestErrorHandling:
    def test_unknown_observation_is_rejected(self, hmm):
        with pytest.raises(ValueError, match="unknown observation"):
            hmm.update("TSUNAMI")

    def test_reset_returns_to_the_prior(self, hmm):
        for _ in range(5):
            hmm.update("RAPIDLY_RISING")
        hmm.reset()
        assert hmm.belief == FLOOD_PRIOR
        assert hmm.observation_history == []


class TestDeterminism:
    def test_the_same_sequence_gives_the_same_belief(self):
        sequence = ["LOW_WATER", "MEDIUM_WATER", "HIGH_WATER", "RAPIDLY_RISING"] * 5
        a = filter_sequence(sequence).belief.distribution
        b = filter_sequence(sequence).belief.distribution
        assert a == b

    def test_order_matters(self):
        forward = filter_sequence(["LOW_WATER"] * 5 + ["RAPIDLY_RISING"] * 5)
        backward = filter_sequence(["RAPIDLY_RISING"] * 5 + ["LOW_WATER"] * 5)
        assert forward.belief.distribution != backward.belief.distribution


class TestEntropy:
    def test_uniform_over_four_states_is_two_bits(self):
        assert entropy_bits({s: 0.25 for s in FLOOD_STATES}) == pytest.approx(2.0)

    def test_certainty_is_zero_bits(self):
        assert entropy_bits({"NORMAL": 1.0, "RISING": 0.0}) == pytest.approx(0.0)

    def test_zero_probabilities_do_not_produce_nan(self):
        assert entropy_bits({"a": 0.5, "b": 0.5, "c": 0.0}) == pytest.approx(1.0)


class TestHistory:
    def test_history_records_every_step(self, hmm):
        for _ in range(7):
            hmm.update("MEDIUM_WATER")
        assert len(hmm.observation_history) == 7
        assert len(hmm.belief_history) == 8  # prior plus one row per update

    def test_history_can_be_bounded(self, hmm):
        for _ in range(50):
            hmm.update("MEDIUM_WATER")
        hmm.trim_history(10)
        assert len(hmm.belief_history) == 10
        assert len(hmm.observation_history) == 10

"""Bayesian Network: CPTs, noisy-OR, virtual evidence, two pathways."""

import math

import pytest

from app.ai.probability.bayesian import (
    RAINFALL_VALUES,
    SURFACE_WATER_VALUES,
    WATER_LEVEL_VALUES,
    discretise_rainfall,
    discretise_road_damage,
    discretise_water_level,
    global_posterior,
    infer,
    noisy_or_failure,
    road_failure_probability,
)
from app.config import (
    FLOOD_SEVERITY_CPT,
    FLOOD_STATES,
    SURFACE_WATER_CPT,
    WATER_LEVEL_CPT,
)


class TestCPTsAreWellFormed:
    @pytest.mark.parametrize(
        "table", [WATER_LEVEL_CPT, FLOOD_SEVERITY_CPT, SURFACE_WATER_CPT]
    )
    def test_every_row_normalises(self, table):
        for key, row in table.items():
            assert math.isclose(sum(row.values()), 1.0, abs_tol=1e-9), key

    def test_flood_severity_covers_every_parent_combination(self):
        for rain in RAINFALL_VALUES:
            for water in WATER_LEVEL_VALUES:
                assert (rain, water) in FLOOD_SEVERITY_CPT

    def test_surface_water_covers_every_parent_combination(self):
        for water in WATER_LEVEL_VALUES:
            for band in ("LOW", "MED", "HIGH"):
                assert (water, band) in SURFACE_WATER_CPT


class TestNoisyOr:
    def test_matches_the_phase_0_anchor_values(self):
        assert noisy_or_failure("NORMAL", "NONE", "DRY") == pytest.approx(0.039, abs=1e-3)
        assert noisy_or_failure("HIGH", "MINOR", "SHALLOW") == pytest.approx(0.695, abs=1e-3)
        assert noisy_or_failure("CRITICAL", "MAJOR", "DEEP") == pytest.approx(0.967, abs=1e-3)

    def test_is_a_probability_for_every_combination(self):
        for s in FLOOD_STATES:
            for d in ("NONE", "MINOR", "MAJOR"):
                for w in SURFACE_WATER_VALUES:
                    assert 0.0 <= noisy_or_failure(s, d, w) <= 1.0

    def test_is_monotone_in_flood_severity(self):
        ordered = ["NORMAL", "RISING", "HIGH", "CRITICAL"]
        for d in ("NONE", "MINOR", "MAJOR"):
            for w in SURFACE_WATER_VALUES:
                values = [noisy_or_failure(s, d, w) for s in ordered]
                assert values == sorted(values)

    def test_is_monotone_in_surface_water(self):
        ordered = ["DRY", "SHALLOW", "DEEP"]
        for s in FLOOD_STATES:
            values = [noisy_or_failure(s, "NONE", w) for w in ordered]
            assert values == sorted(values)

    def test_the_leak_means_no_road_is_ever_perfectly_safe(self):
        assert noisy_or_failure("NORMAL", "NONE", "DRY") > 0.0


class TestDiscretisation:
    @pytest.mark.parametrize(
        "mm,expected", [(0.0, "LOW"), (4.9, "LOW"), (5.0, "MED"), (19.9, "MED"), (20.0, "HIGH")]
    )
    def test_rainfall_bands(self, mm, expected):
        assert discretise_rainfall(mm) == expected

    @pytest.mark.parametrize(
        "m,expected", [(0.0, "LOW"), (1.49, "LOW"), (1.5, "MED"), (2.79, "MED"), (2.8, "HIGH")]
    )
    def test_water_level_bands(self, m, expected):
        assert discretise_water_level(m) == expected

    @pytest.mark.parametrize(
        "level,expected", [(0.0, "NONE"), (0.19, "NONE"), (0.2, "MINOR"), (0.6, "MAJOR")]
    )
    def test_damage_bands(self, level, expected):
        assert discretise_road_damage(level) == expected


class TestGlobalPosterior:
    def test_posterior_normalises(self):
        result = global_posterior(rainfall_evidence="HIGH", water_level_evidence="HIGH")
        assert math.isclose(sum(result.flood_severity.values()), 1.0, abs_tol=1e-9)

    def test_severe_evidence_shifts_mass_to_severe_states(self):
        calm = global_posterior(rainfall_evidence="LOW", water_level_evidence="LOW")
        storm = global_posterior(rainfall_evidence="HIGH", water_level_evidence="HIGH")
        assert storm.flood_severity["CRITICAL"] > calm.flood_severity["CRITICAL"]
        assert storm.flood_severity["NORMAL"] < calm.flood_severity["NORMAL"]

    def test_virtual_evidence_changes_the_posterior(self):
        without = global_posterior(rainfall_evidence="MED", water_level_evidence="MED")
        with_hmm = global_posterior(
            rainfall_evidence="MED",
            water_level_evidence="MED",
            hmm_belief={"NORMAL": 0.0, "RISING": 0.0, "HIGH": 0.1, "CRITICAL": 0.9},
        )
        assert with_hmm.flood_severity["CRITICAL"] > without.flood_severity["CRITICAL"]
        assert with_hmm.used_virtual_evidence
        assert not without.used_virtual_evidence

    def test_the_two_sources_combine_rather_than_one_overriding(self):
        """A sensor spike disagreeing with a smoothed belief must land between."""
        sensors_only = global_posterior(
            rainfall_evidence="HIGH", water_level_evidence="HIGH"
        )
        combined = global_posterior(
            rainfall_evidence="HIGH",
            water_level_evidence="HIGH",
            hmm_belief={"NORMAL": 0.7, "RISING": 0.3, "HIGH": 0.0, "CRITICAL": 0.0},
        )
        # The HMM says calm, the sensors say storm: the posterior must move
        # towards calm without ignoring the sensors.
        assert combined.flood_severity["CRITICAL"] < sensors_only.flood_severity["CRITICAL"]

    def test_a_contradictory_belief_falls_back_rather_than_dividing_by_zero(self):
        result = global_posterior(
            rainfall_evidence="LOW",
            water_level_evidence="LOW",
            hmm_belief={"NORMAL": 0.0, "RISING": 0.0, "HIGH": 0.0, "CRITICAL": 0.0},
        )
        assert math.isclose(sum(result.flood_severity.values()), 1.0, abs_tol=1e-9)
        assert not result.used_virtual_evidence


class TestTwoPathways:
    """The property that makes this a network rather than a relabelled HMM."""

    def test_terrain_discriminates_between_roads_under_identical_belief(self):
        posterior = global_posterior(
            rainfall_evidence="MED", water_level_evidence="MED"
        )
        low = road_failure_probability(
            severity_posterior=posterior.flood_severity,
            water_level_posterior=posterior.water_level,
            elevation_band="LOW",
            damage_level=0.0,
        )
        high = road_failure_probability(
            severity_posterior=posterior.flood_severity,
            water_level_posterior=posterior.water_level,
            elevation_band="HIGH",
            damage_level=0.0,
        )
        assert low > high, (
            "terrain must change P(failure) even with one global belief; "
            "if it does not, the SurfaceWater pathway is not contributing"
        )

    def test_water_level_reaches_roads_without_passing_through_severity(self):
        """Hold FloodSeverity fixed and vary only the water posterior."""
        fixed_severity = {"NORMAL": 0.0, "RISING": 1.0, "HIGH": 0.0, "CRITICAL": 0.0}
        dry = road_failure_probability(
            severity_posterior=fixed_severity,
            water_level_posterior={"LOW": 1.0, "MED": 0.0, "HIGH": 0.0},
            elevation_band="LOW",
            damage_level=0.0,
        )
        wet = road_failure_probability(
            severity_posterior=fixed_severity,
            water_level_posterior={"LOW": 0.0, "MED": 0.0, "HIGH": 1.0},
            elevation_band="LOW",
            damage_level=0.0,
        )
        assert wet > dry, "the second pathway is dead; the BN adds nothing to the HMM"

    def test_damage_raises_failure_probability(self):
        posterior = global_posterior(rainfall_evidence="MED", water_level_evidence="MED")
        kwargs = {
            "severity_posterior": posterior.flood_severity,
            "water_level_posterior": posterior.water_level,
            "elevation_band": "MED",
        }
        assert road_failure_probability(**kwargs, damage_level=0.8) > \
            road_failure_probability(**kwargs, damage_level=0.0)


class TestInfer:
    def test_returns_a_probability_for_every_road(self):
        roads = {"R1": ("LOW", 0.0), "R2": ("MED", 0.3), "R3": ("HIGH", 0.0)}
        result = infer(roads=roads, rainfall_evidence="MED", water_level_evidence="MED")
        assert set(result.per_road) == {"R1", "R2", "R3"}
        assert all(0.0 <= p <= 1.0 for p in result.per_road.values())

    def test_ranks_roads_by_terrain(self):
        roads = {"low": ("LOW", 0.0), "med": ("MED", 0.0), "high": ("HIGH", 0.0)}
        result = infer(roads=roads, rainfall_evidence="HIGH", water_level_evidence="HIGH")
        assert result.per_road["low"] > result.per_road["med"] > result.per_road["high"]

    def test_reports_execution_time(self):
        result = infer(roads={"R1": ("LOW", 0.0)})
        assert result.execution_ms >= 0.0

    def test_is_deterministic(self):
        roads = {"R1": ("LOW", 0.1), "R2": ("HIGH", 0.0)}
        a = infer(roads=roads, rainfall_evidence="MED", water_level_evidence="HIGH")
        b = infer(roads=roads, rainfall_evidence="MED", water_level_evidence="HIGH")
        assert a.per_road == b.per_road

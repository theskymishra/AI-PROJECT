"""Determinism of the keyed RNG."""

import pytest

from app.simulation.rng import derive_rng, weighted_choice


def test_same_key_gives_the_same_stream():
    a = [derive_rng(1, 5, "x").random() for _ in range(3)]
    b = [derive_rng(1, 5, "x").random() for _ in range(3)]
    assert a == b


def test_different_tick_gives_a_different_value():
    assert derive_rng(1, 5, "x").random() != derive_rng(1, 6, "x").random()


def test_different_channel_gives_a_different_value():
    assert derive_rng(1, 5, "x").random() != derive_rng(1, 5, "y").random()


def test_different_seed_gives_a_different_value():
    assert derive_rng(1, 5, "x").random() != derive_rng(2, 5, "x").random()


def test_streams_are_independent_of_call_order():
    """The property sequential seeding would destroy.

    Draw channel B before channel A; A's value must be unchanged. This is what
    lets a later phase add a new random consumer without shifting an existing
    one's values and silently breaking a working demo.
    """
    a_first = derive_rng(7, 42, "a").random()
    derive_rng(7, 42, "b").random()
    a_again = derive_rng(7, 42, "a").random()
    assert a_first == a_again


def test_weighted_choice_respects_the_distribution():
    rng = derive_rng(1, 1, "t")
    counts = {"a": 0, "b": 0}
    for tick in range(4000):
        counts[weighted_choice(derive_rng(1, tick, "t"), {"a": 0.25, "b": 0.75})] += 1
    assert 0.20 < counts["a"] / 4000 < 0.30


def test_weighted_choice_is_insensitive_to_key_order():
    forward = weighted_choice(derive_rng(3, 9, "k"), {"a": 0.3, "b": 0.7})
    reverse = weighted_choice(derive_rng(3, 9, "k"), {"b": 0.7, "a": 0.3})
    assert forward == reverse


def test_weighted_choice_always_returns_a_declared_key():
    for tick in range(200):
        assert weighted_choice(
            derive_rng(1, tick, "t"), {"a": 0.1, "b": 0.1, "c": 0.8}
        ) in {"a", "b", "c"}


def test_weighted_choice_rejects_a_degenerate_distribution():
    with pytest.raises(ValueError, match="positive value"):
        weighted_choice(derive_rng(1, 1, "t"), {"a": 0.0})

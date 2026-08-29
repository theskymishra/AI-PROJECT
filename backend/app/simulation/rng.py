"""Deterministic randomness.

There is no module-level ``random`` anywhere in this project. Every random draw
goes through ``derive_rng``, which is a pure function of (seed, tick, channel).

Why keyed rather than sequential: a sequentially-advanced generator couples every
consumer to every other consumer's call order. Adding a new random consumer in
Phase 5 would silently shift the values an existing Phase 2 consumer receives,
breaking a demo that worked yesterday for no visible reason. Keying by tick makes
each stream independent, so consumers can be added, removed or reordered freely.

It also means pausing, resuming and changing speed cannot perturb anything: the
value drawn on tick 150 depends on the number 150, not on how long the process
has been running or how fast it got there.
"""

from __future__ import annotations

import hashlib
import random

#: Channels currently in use. Listed so that a duplicate is obvious on review.
CHANNELS = (
    "sensor.water",
    "sensor.rain",
    "sensor.river",
    "sensor.emission",
    "emergency.spawn",
)


def derive_rng(seed: int, tick: int, channel: str) -> random.Random:
    """Return a generator determined entirely by (seed, tick, channel).

    Args:
        seed: Master seed from configuration.
        tick: Simulation tick. Integer, never a wall-clock time.
        channel: Namespace for this consumer, e.g. "sensor.water".

    Returns:
        A freshly seeded ``random.Random``. Callers should draw and discard it;
        holding one across ticks would reintroduce the coupling this avoids.
    """
    digest = hashlib.blake2b(
        f"{seed}:{tick}:{channel}".encode("utf-8"), digest_size=8
    ).digest()
    return random.Random(int.from_bytes(digest, "big"))


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """Sample a key from a probability distribution.

    Uses a cumulative sweep in sorted key order rather than
    ``random.choices``, so the result depends only on the distribution's
    contents and not on Python's dict insertion order.
    """
    keys = sorted(weights)
    total = sum(weights[k] for k in keys)
    if total <= 0:
        raise ValueError(f"weights must sum to a positive value, got {total}")
    threshold = rng.random() * total
    cumulative = 0.0
    for key in keys:
        cumulative += weights[key]
        if threshold < cumulative:
            return key
    return keys[-1]

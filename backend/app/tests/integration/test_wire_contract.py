"""The SSE tick payload wire contract.

These tests exist because two real defects shipped past a green build and a
clean typecheck, and only surfaced when a client actually consumed the stream:

  1. timeline_tail and alerts_tail were omitted when empty. An
     intermittently-absent field is a contract clients get wrong; it threw a
     TypeError in the dashboard reducer on the first quiet tick.

  2. `roads` carries ONLY changed roads. A client that assigns it over its
     local array loses every road the delta does not mention -- 37 of 38 the
     first time one road closes.

Neither is visible to a type checker on either side of the wire. They are
locked down here.
"""

import pytest

from app.simulation.engine import SimulationEngine

#: Present on every tick frame, always the complete set.
COMPLETE_FIELDS = {
    "clock",
    "environment",
    "stats",
    "sensors",
    "hospitals",
    "timeline_tail",
    "alerts_tail",
}

#: Present only when changed, and containing only what changed.
PARTIAL_FIELDS = {"roads", "emergencies"}


@pytest.fixture
def ticks():
    """Every tick frame from a full SEVERE_FLOOD run."""
    engine = SimulationEngine()
    captured: list[dict] = []
    engine.broadcaster.publish = lambda **kw: captured.append(kw)  # type: ignore[method-assign]
    engine.set_scenario("SEVERE_FLOOD")
    engine.advance(240)
    return [c for c in captured if c["type"] == "tick"]


def test_the_run_produces_tick_frames(ticks):
    assert len(ticks) == 240


def test_complete_fields_are_present_on_every_single_tick(ticks):
    """No field may be intermittently absent."""
    for frame in ticks:
        missing = COMPLETE_FIELDS - set(frame["payload"])
        assert not missing, f"tick {frame['tick']} is missing {sorted(missing)}"


def test_tail_fields_are_present_even_when_nothing_happened(ticks):
    """The regression that crashed the dashboard reducer."""
    quiet = [f for f in ticks if f["tick"] < 25]
    assert quiet, "expected some quiet early ticks"
    for frame in quiet:
        assert "timeline_tail" in frame["payload"]
        assert "alerts_tail" in frame["payload"]
        assert isinstance(frame["payload"]["timeline_tail"], list)
        assert isinstance(frame["payload"]["alerts_tail"], list)


def test_no_unexpected_fields_appear_on_the_wire(ticks):
    allowed = COMPLETE_FIELDS | PARTIAL_FIELDS
    for frame in ticks:
        unexpected = set(frame["payload"]) - allowed
        assert not unexpected, f"tick {frame['tick']} sent {sorted(unexpected)}"


def test_road_deltas_are_partial_not_complete(ticks):
    """Documents the semantics a client must implement.

    If this ever starts failing because every delta contains all 38 roads,
    the merge-by-id logic in the frontend reducer is no longer load-bearing --
    but do not remove it without changing this test deliberately.
    """
    sizes = {len(f["payload"]["roads"]) for f in ticks if "roads" in f["payload"]}
    assert sizes, "expected at least one road delta during SEVERE_FLOOD"
    assert min(sizes) < 38, (
        "road deltas are supposed to be partial; a client merging by id "
        f"depends on it. Sizes seen: {sorted(sizes)}"
    )


def test_partial_fields_are_absent_rather_than_empty(ticks):
    """A partial field is omitted when nothing changed, never sent as []."""
    for frame in ticks:
        for field in PARTIAL_FIELDS:
            if field in frame["payload"]:
                assert frame["payload"][field], (
                    f"tick {frame['tick']} sent an empty {field} list; omit it instead"
                )


def test_hospitals_are_always_complete(ticks):
    for frame in ticks:
        assert len(frame["payload"]["hospitals"]) == 3


def test_sensors_are_always_complete(ticks):
    for frame in ticks:
        assert len(frame["payload"]["sensors"]) == 6


def test_sequence_numbers_are_strictly_monotonic(ticks):
    seqs = [f["seq"] for f in ticks]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs), "duplicate seq values would break gap detection"


def test_merging_road_deltas_reconstructs_the_full_world(ticks):
    """Replay the deltas the way the frontend reducer does.

    This is the frontend's merge algorithm, executed against real frames. If
    it ends with fewer than 38 roads, the dashboard map would have holes.
    """
    engine = SimulationEngine()
    engine.set_scenario("SEVERE_FLOOD")
    roads = {r["id"]: r for r in engine.snapshot()["roads"]}
    assert len(roads) == 38

    for frame in ticks:
        for road in frame["payload"].get("roads", []):
            roads[road["id"]] = road  # merge by id, never replace

    assert len(roads) == 38, "merging deltas must never lose roads"
    assert roads["R17"]["blocked"] is True, "R17 closes during SEVERE_FLOOD"

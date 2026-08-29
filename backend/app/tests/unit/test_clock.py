"""Simulation clock semantics."""

import pytest

from app.config import MAX_TICKS_PER_PUMP
from app.models.common import SimStatus
from app.simulation.clock import SimulationClock


def test_starts_idle_at_tick_zero():
    clock = SimulationClock()
    assert clock.tick == 0
    assert clock.status is SimStatus.IDLE
    assert clock.speed == 1


def test_paused_clock_yields_no_ticks():
    clock = SimulationClock()
    clock.start(now=0.0)
    clock.pause()
    assert clock.pump(now=10.0) == 0


def test_idle_clock_yields_no_ticks():
    assert SimulationClock().pump(now=100.0) == 0


def test_one_second_at_1x_is_one_tick():
    clock = SimulationClock()
    clock.start(now=0.0)
    assert clock.pump(now=1.0) == 1


def test_one_second_at_5x_is_five_ticks():
    clock = SimulationClock()
    clock.start(now=0.0)
    clock.set_speed(5)
    assert clock.pump(now=1.0) == 5


def test_fractional_time_accumulates_rather_than_rounding_away():
    """Ten 100 ms polls at 1x must yield exactly one tick, not zero."""
    clock = SimulationClock()
    clock.start(now=0.0)
    total = sum(clock.pump(now=0.1 * i) for i in range(1, 11))
    assert total == 1


def test_backlog_is_capped_not_replayed():
    clock = SimulationClock()
    clock.start(now=0.0)
    assert clock.pump(now=10_000.0) == MAX_TICKS_PER_PUMP


def test_resume_does_not_credit_time_spent_paused():
    clock = SimulationClock()
    clock.start(now=0.0)
    clock.pause()
    clock.resume(now=500.0)
    assert clock.pump(now=500.5) == 0
    assert clock.pump(now=501.0) == 1


def test_speed_change_does_not_move_the_tick_counter():
    clock = SimulationClock()
    clock.start(now=0.0)
    clock.advance_one()
    before = clock.tick
    clock.set_speed(5)
    assert clock.tick == before


@pytest.mark.parametrize("speed", [0, 3, 4, 10, -1])
def test_unsupported_speeds_are_rejected(speed):
    with pytest.raises(ValueError, match="speed must be one of"):
        SimulationClock().set_speed(speed)


def test_reset_returns_everything_to_initial_state():
    clock = SimulationClock()
    clock.start(now=0.0)
    clock.set_speed(5)
    clock.advance_one()
    clock.reset()
    assert (clock.tick, clock.speed, clock.status) == (0, 1, SimStatus.IDLE)


@pytest.mark.parametrize(
    "tick,label", [(0, "00:00"), (59, "00:59"), (60, "01:00"), (163, "02:43"), (3661, "1:01:01")]
)
def test_elapsed_label_formatting(tick, label):
    clock = SimulationClock()
    clock.tick = tick
    assert clock.elapsed_label == label

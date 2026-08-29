"""Simulation clock.

One tick is one simulated second. Speed controls how many ticks are CONSUMED
per real second; it never changes what happens on a given tick. That separation
is the whole reason a scenario run at 5x produces an identical event log to the
same scenario run at 1x.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import ALLOWED_SPEEDS, MAX_TICKS_PER_PUMP
from app.models.common import SimStatus


@dataclass
class SimulationClock:
    """Tick counter with run/pause semantics and a real-time pump."""

    tick: int = 0
    speed: int = 1
    status: SimStatus = SimStatus.IDLE

    #: Fractional ticks carried between pumps, so a 100 ms poll at 1x does not
    #: round down to zero forever.
    _accumulator: float = field(default=0.0, repr=False)
    _last_wall: float | None = field(default=None, repr=False)

    # -- control -----------------------------------------------------------

    def start(self, now: float) -> None:
        self.status = SimStatus.RUNNING
        self._last_wall = now
        self._accumulator = 0.0

    def pause(self) -> None:
        if self.status is SimStatus.RUNNING:
            self.status = SimStatus.PAUSED
            self._last_wall = None

    def resume(self, now: float) -> None:
        if self.status is SimStatus.PAUSED:
            self.status = SimStatus.RUNNING
            self._last_wall = now
            self._accumulator = 0.0

    def complete(self) -> None:
        self.status = SimStatus.COMPLETED
        self._last_wall = None

    def reset(self) -> None:
        self.tick = 0
        self.speed = 1
        self.status = SimStatus.IDLE
        self._accumulator = 0.0
        self._last_wall = None

    def set_speed(self, speed: int) -> None:
        if speed not in ALLOWED_SPEEDS:
            raise ValueError(
                f"speed must be one of {ALLOWED_SPEEDS}, got {speed}"
            )
        self.speed = speed

    # -- advancement -------------------------------------------------------

    def pump(self, now: float) -> int:
        """Return how many ticks are due since the last pump.

        Returns 0 unless the clock is RUNNING. Capped at MAX_TICKS_PER_PUMP so
        a laptop resuming from sleep does not try to replay an hour of
        simulation inside one iteration of the event loop.
        """
        if self.status is not SimStatus.RUNNING:
            self._last_wall = now
            return 0

        if self._last_wall is None:
            self._last_wall = now
            return 0

        elapsed = max(0.0, now - self._last_wall)
        self._last_wall = now
        self._accumulator += elapsed * self.speed

        due = int(self._accumulator)
        if due <= 0:
            return 0

        self._accumulator -= due
        if due > MAX_TICKS_PER_PUMP:
            # Drop the backlog rather than replaying it. Catching up would
            # freeze the UI and, worse, run scenario events far faster than
            # the operator can see them.
            self._accumulator = 0.0
            due = MAX_TICKS_PER_PUMP
        return due

    def advance_one(self) -> int:
        self.tick += 1
        return self.tick

    # -- display -----------------------------------------------------------

    @property
    def elapsed_label(self) -> str:
        """MM:SS, or HH:MM:SS past an hour."""
        hours, remainder = divmod(self.tick, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

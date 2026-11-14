"""Runs the simulation in real time: a timer, two clocks, and a limit on the work per frame.

Two clocks
----------
Real time comes from a monotonic clock, one that never jumps backwards or forwards when the
computer's wall clock is corrected. Simulated time belongs to the
:class:`bhlab.simulation.model.Simulation`. On every frame the runner measures how much real
time has passed since the previous frame and asks the simulation to advance by

    Δt_simulated = speed × Δt_real

The frame rate decides only how often this happens. It never enters the physics: the states at
a given simulated time are the same at any frame rate (see :mod:`bhlab.simulation.model`).

When there is too much to compute
---------------------------------
A fast speed with a particle close to the black hole can demand more solver steps per second
than the computer can deliver. Two limits keep the window usable:

- At most ``COMPUTE_BUDGET_SECONDS`` of each frame is spent computing. If that is not enough,
  simulated time advances by less than the speed asked for, and :attr:`is_behind` reports it.
- A gap of more than ``MAX_FRAME_SECONDS`` between two frames (the window was frozen, the
  computer slept) counts as that much and no more, so the simulation does not leap ahead.

In both cases only the pace changes. The motion stays correct.
"""

import math
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from bhlab.simulation.model import Simulation


class SimulationRunner(QObject):
    """Advances a simulation in real time and announces when there is something new to show."""

    changed = Signal()
    """Emitted whenever the simulation has moved on or has been reset."""

    running_changed = Signal(bool)
    """Emitted when the simulation starts or stops running."""

    FRAME_MILLISECONDS = 16  # about 60 frames per second
    MAX_FRAME_SECONDS = 0.1
    COMPUTE_BUDGET_SECONDS = 0.008
    STEP_SECONDS = 0.1  # the Step button advances by this much playback time
    _BEHIND_MEMORY_FRAMES = 30  # keep reporting "behind" for half a second, so it does not flicker

    def __init__(
        self,
        simulation: Simulation,
        *,
        speed: float = 100.0,
        clock: Callable[[], float] = time.perf_counter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.simulation = simulation
        self._clock = clock
        self._speed = 0.0
        self.set_speed(speed)
        self._last_frame = 0.0
        self._behind_frames = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MILLISECONDS)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.tick)

    # --- state --------------------------------------------------------------------------

    @property
    def speed(self) -> float:
        """Simulated time, in GM/c³, per second of real time."""
        return self._speed

    @property
    def is_running(self) -> bool:
        """Whether simulated time is running."""
        return self._timer.isActive()

    @property
    def is_behind(self) -> bool:
        """Whether the simulation has recently advanced by less than the speed asked for."""
        return self._behind_frames > 0

    # --- what the controls ask for ------------------------------------------------------

    def set_speed(self, speed: float) -> None:
        """Set the speed, in GM/c³ of simulated time per second of real time."""
        if not (math.isfinite(speed) and speed > 0.0):
            raise ValueError(f"The speed must be a positive, finite number; got {speed!r}")
        self._speed = float(speed)

    def set_running(self, running: bool) -> None:
        """Start or stop the passage of simulated time."""
        if running == self.is_running:
            return
        if running:
            self._last_frame = self._clock()
            self._timer.start()
        else:
            self._timer.stop()
            self._behind_frames = 0
        self.running_changed.emit(running)

    def step(self) -> None:
        """Advance by ``STEP_SECONDS`` of playback at the current speed. For use while paused."""
        self.simulation.advance(self._speed * self.STEP_SECONDS)
        self.changed.emit()

    def reset(self) -> None:
        """Pause, and put the simulation back at time zero."""
        self.set_running(False)
        self.simulation.reset()
        self.changed.emit()

    def tick(self) -> None:
        """One frame: advance the simulation by the real time that has passed since the last."""
        now = self._clock()
        elapsed = min(now - self._last_frame, self.MAX_FRAME_SECONDS)
        self._last_frame = now
        deadline = now + self.COMPUTE_BUDGET_SECONDS
        covered = self.simulation.advance(
            self._speed * elapsed, keep_going=lambda: self._clock() < deadline
        )
        self._behind_frames = (
            max(self._behind_frames - 1, 0) if covered else self._BEHIND_MEMORY_FRAMES
        )
        self.changed.emit()

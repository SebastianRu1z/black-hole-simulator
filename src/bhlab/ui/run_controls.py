"""The bar under the map: play, pause, step and reset, the speed, and the simulation clock.

The speed is how much simulated time passes in one second of real time. Simulated time is
measured in GM/c³, so the same speed means very different things for different black holes:
100 GM/c³ per second is slow motion for a stellar-mass black hole (4.9 ms of its time per second
on screen) and a fast-forward for Sagittarius A* (35 minutes per second). The bar shows both.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bhlab.formatting import format_number, format_time_convenient
from bhlab.ui.theme import set_style_flag
from bhlab.units import BlackHole


def format_clock(time: float) -> str:
    """Simulated time for the clock: one decimal while that stays readable, then a × 10ⁿ."""
    return f"{time:.1f}" if abs(time) < 1e7 else format_number(time, sig=6)


class RunControls(QFrame):
    """Transport controls for the simulation. It only reports what the user asks for."""

    play_toggled = Signal(bool)
    """Emitted with True when the user presses Play and with False for Pause."""

    step_requested = Signal()
    reset_requested = Signal()

    speed_changed = Signal(float)
    """Emitted with the new speed, in GM/c³ of simulated time per second of real time."""

    SPEEDS: tuple[float, ...] = (
        *(float(mantissa * 10**decade) for decade in range(5) for mantissa in (1, 2, 5)),
        100_000.0,
    )
    """The speeds the slider offers: 1, 2, 5, 10, … up to 100 000 GM/c³ per second."""

    DEFAULT_SPEED = 100.0

    def __init__(self, black_hole: BlackHole, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("runPanel")
        self._black_hole = black_hole
        self._time = 0.0

        self.play_button = self._button("Play", "Let simulated time run (Pause stops it)")
        self.play_button.setCheckable(True)
        self.step_button = self._button(
            "Step", "While paused: advance by a tenth of a second of playback at this speed"
        )
        self.reset_button = self._button(
            "Reset", "Pause, go back to t = 0 and put every particle back at its start"
        )

        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setToolTip(
            "Simulated time since the start, in units of GM/c³ and as physical time for the "
            "chosen mass."
        )

        speed_caption = QLabel("Speed")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, len(self.SPEEDS) - 1)
        self.speed_slider.setPageStep(3)  # one decade
        self.speed_slider.setValue(self.SPEEDS.index(self.DEFAULT_SPEED))
        self.speed_slider.setFixedWidth(150)
        self.speed_slider.setToolTip(
            "Simulated time per second of real time, from 1 to 100 000 GM/c³ per second."
        )
        self.speed_label = QLabel()
        # Under the speed: what it means in physical time or, when the computer cannot keep
        # up, a notice that simulated time is advancing more slowly than this.
        self._behind = False
        self.speed_detail_label = QLabel()
        self.speed_detail_label.setObjectName("helperLabel")
        self.speed_detail_label.setToolTip(
            "How much of the black hole's own time passes in one second on screen. If the "
            "computer cannot compute that much, the motion stays correct and simulated time "
            "simply advances more slowly; a notice appears here."
        )
        readout = QVBoxLayout()
        readout.setSpacing(0)
        readout.addWidget(self.speed_label)
        readout.addWidget(self.speed_detail_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for button in (self.play_button, self.step_button, self.reset_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.clock_label)

        speed = QHBoxLayout()
        speed.setSpacing(10)
        speed.addWidget(speed_caption)
        speed.addWidget(self.speed_slider)
        speed.addLayout(readout)
        speed.addStretch(1)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(8)
        layout.addLayout(buttons)
        layout.addLayout(speed)

        self.play_button.clicked.connect(self._on_play_clicked)
        self.step_button.clicked.connect(self.step_requested)
        self.reset_button.clicked.connect(self.reset_requested)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

        self._refresh_clock()
        self._refresh_speed()

    # --- public interface ---------------------------------------------------------------

    def speed(self) -> float:
        """The chosen speed, in GM/c³ per second of real time."""
        return self.SPEEDS[self.speed_slider.value()]

    def set_black_hole(self, black_hole: BlackHole) -> None:
        """Use ``black_hole`` to express simulated time as physical time."""
        self._black_hole = black_hole
        self._refresh_clock()
        self._refresh_speed()

    def set_time(self, time: float) -> None:
        """Show ``time``, the simulated time in GM/c³, on the clock."""
        self._time = time
        self._refresh_clock()

    def set_running(self, running: bool) -> None:
        """Show whether the simulation is running. Does not emit ``play_toggled``."""
        self.play_button.setChecked(running)
        self.play_button.setText("Pause" if running else "Play")
        self.step_button.setEnabled(not running)

    def set_behind(self, behind: bool) -> None:
        """Show or hide the notice that the simulation cannot keep up with the speed."""
        if behind != self._behind:
            self._behind = behind
            self._refresh_speed()

    # --- internals ----------------------------------------------------------------------

    def _button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("runButton")
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _on_play_clicked(self, checked: bool) -> None:
        self.set_running(checked)
        self.play_toggled.emit(checked)

    def _on_speed_changed(self, _position: int) -> None:
        self._refresh_speed()
        self.speed_changed.emit(self.speed())

    def _refresh_clock(self) -> None:
        physical = format_time_convenient(self._black_hole.time_to_si(self._time))
        self.clock_label.setText(f"t = {format_clock(self._time)} GM/c³  =  {physical}")

    def _refresh_speed(self) -> None:
        self.speed_label.setText(f"{self.speed():,.0f} GM/c³ per second")
        if self._behind:
            detail = "running slower than this: too much to compute"
        else:
            physical = format_time_convenient(self._black_hole.time_to_si(self.speed()))
            detail = f"1 s on screen = {physical}"
        self.speed_detail_label.setText(detail)
        set_style_flag(self.speed_detail_label, "error", self._behind)

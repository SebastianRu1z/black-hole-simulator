"""Small actions shared by the interface tests: do what a user's hands would do."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def type_mass(window, text, *, press_enter=True):
    """Replace the content of the mass field by typing, as a user would."""
    edit = window.controls.mass_edit
    edit.setFocus()
    edit.selectAll()
    QTest.keyClick(edit, Qt.Key.Key_Delete)
    QTest.keyClicks(edit, text)
    if press_enter:
        QTest.keyClick(edit, Qt.Key.Key_Return)


def click(button):
    """Click a button with the left mouse button."""
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)


class FakeClock:
    """Real time under the test's control, in seconds. Stands in for time.perf_counter.

    ``cost_per_reading`` makes every reading of the clock take that long, which is how a test
    pretends that computing is slow.
    """

    def __init__(self):
        self.now = 0.0
        self.cost_per_reading = 0.0

    def __call__(self):
        reading = self.now
        self.now += self.cost_per_reading
        return reading

    def advance(self, seconds):
        self.now += seconds


def run_for(runner, clock, real_seconds, frames_per_second=60.0):
    """Let ``real_seconds`` of real time pass in frames, calling the runner as its timer would."""
    frame = 1.0 / frames_per_second
    remaining = real_seconds
    while remaining > 1e-12:
        elapsed = min(frame, remaining)
        clock.advance(elapsed)
        runner.tick()
        remaining -= elapsed


def fill_particle_form(form, x, y, vx, vy):
    """Type a starting position and velocity into the particle form."""
    for name, value in zip(form.FIELDS, (x, y, vx, vy), strict=True):
        form.edits[name].setText(str(value))

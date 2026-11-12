"""The application window, driven the way a user would drive it.

These tests run on Qt's offscreen platform (see conftest.py), so no window appears.
"""

import pytest
from helpers import type_mass
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from bhlab.ui.app import run
from bhlab.ui.mass_controls import PRESETS, mass_to_text, parse_mass_text

# --- the window ------------------------------------------------------------------------------


def test_window_opens_showing_a_ten_solar_mass_black_hole(window):
    assert window.windowTitle() == "Black Hole Physics Lab"
    assert window.black_hole.mass_solar == pytest.approx(10.0)
    assert window.controls.mass_edit.text() == "10"
    assert window.scales.value_text("mass") == ("1.988 × 10³¹ kg", "10.00 M☉")
    assert window.scales.value_text("gravitational_radius") == ("14.77 km", "9.871 × 10⁻⁸ AU")
    assert window.scales.value_text("event_horizon") == ("29.53 km", "1.974 × 10⁻⁷ AU")
    assert window.scales.value_text("photon_sphere")[0] == "44.30 km"
    assert window.scales.value_text("isco")[0] == "88.60 km"
    assert window.scales.value_text("time_unit") == ("4.925 × 10⁻⁵ s", "49.25 µs")


def test_typing_a_mass_and_pressing_enter_updates_every_scale(window):
    type_mass(window, "4.3e6")
    assert window.black_hole.mass_solar == pytest.approx(4.3e6)
    assert window.scales.value_text("mass")[1] == "4.300 × 10⁶ M☉"
    assert window.scales.value_text("event_horizon") == ("1.270 × 10⁷ km", "0.08489 AU")
    assert window.scales.value_text("time_unit")[1] == "21.18 s"
    assert window.controls.error_text() == ""


def test_nothing_changes_until_enter_is_pressed(window):
    type_mass(window, "4.3e6", press_enter=False)
    assert window.black_hole.mass_solar == pytest.approx(10.0)
    QTest.keyClick(window.controls.mass_edit, Qt.Key.Key_Return)
    assert window.black_hole.mass_solar == pytest.approx(4.3e6)


@pytest.mark.parametrize("text", ["abc", "-5", "0", "4,3", "", "1e999", "nan"])
def test_invalid_input_is_reported_and_never_applied(window, text):
    type_mass(window, text)
    assert window.controls.error_text() != ""
    assert "still shows 10 M☉" in window.controls.error_text()
    assert window.controls.message_label.text() == window.controls.error_text()
    assert window.controls.message_label.property("error") is True
    assert window.controls.mass_edit.property("invalid") is True
    assert window.black_hole.mass_solar == pytest.approx(10.0)
    assert window.scales.value_text("event_horizon")[0] == "29.53 km"


def test_error_clears_once_a_valid_mass_is_entered(window):
    type_mass(window, "abc")
    assert window.controls.error_text() != ""
    type_mass(window, "25")
    assert window.controls.error_text() == ""
    assert window.controls.message_label.text().startswith("Type a mass")
    assert window.controls.message_label.property("error") is False
    assert window.controls.mass_edit.property("invalid") is False
    assert window.black_hole.mass_solar == pytest.approx(25.0)


def test_each_preset_button_applies_its_mass(window):
    for button, preset in zip(window.controls.preset_buttons, PRESETS, strict=True):
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert window.black_hole.mass_solar == pytest.approx(preset.solar_masses)
        assert window.controls.mass_edit.text() == mass_to_text(preset.solar_masses)
        checked = [b.isChecked() for b in window.controls.preset_buttons]
        assert checked.count(True) == 1
        assert button.isChecked()


def test_no_preset_is_highlighted_for_another_mass(window):
    type_mass(window, "123")
    assert not any(button.isChecked() for button in window.controls.preset_buttons)


def test_slider_is_logarithmic(window):
    window.controls.slider.setValue(600)
    assert window.black_hole.mass_solar == pytest.approx(1e6)
    assert window.controls.mass_edit.text() == "1e6"
    window.controls.slider.setValue(1100)
    assert window.black_hole.mass_solar == pytest.approx(1e11)


def test_typed_mass_moves_the_slider(window):
    type_mass(window, "1e9")
    assert window.controls.slider.value() == 900


def test_a_mass_outside_the_slider_range_is_still_accepted(window):
    type_mass(window, "1e-6")
    assert window.black_hole.mass_solar == pytest.approx(1e-6)
    assert window.controls.slider.value() == window.controls.slider.minimum()
    assert window.scales.value_text("event_horizon")[0] == "2.953 mm"


# --- text handling ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("10", 10.0), ("  4.3e6 ", 4.3e6), ("6.5E9", 6.5e9), ("0.5", 0.5), ("1e-6", 1e-6)],
)
def test_parse_mass_text_accepts_ordinary_numbers(text, expected):
    assert parse_mass_text(text) == expected


@pytest.mark.parametrize(
    "text", ["", "   ", "abc", "4,3", "1,000", "-1", "0", "nan", "inf", "1e999", "1e300"]
)
def test_parse_mass_text_rejects_everything_else(text):
    with pytest.raises(ValueError):
        parse_mass_text(text)


@pytest.mark.parametrize(
    ("mass", "expected"),
    [(10.0, "10"), (0.5, "0.5"), (4.3e6, "4.3e6"), (6.5e9, "6.5e9"), (1e-6, "1e-6")],
)
def test_mass_to_text_is_compact_and_reads_back(mass, expected):
    assert mass_to_text(mass) == expected
    assert parse_mass_text(expected) == mass


# --- start-up --------------------------------------------------------------------------------


def test_application_starts_and_exits_cleanly(qapp):
    assert run([], quit_after_ms=50) == 0

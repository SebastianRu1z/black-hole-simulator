"""The command line: python -m bhlab.orbit."""

import subprocess
import sys

import pytest

from bhlab.orbit import main


def run_cli(capsys, *arguments):
    code = main(list(arguments))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def event_rows(out, name):
    """Rows of the event table for ``name``; unlike the elements block they carry no unit."""
    return [
        line for line in out.splitlines() if line.startswith(f"  {name} ") and "GM/c" not in line
    ]


def test_default_run_describes_the_a_100_ellipse(capsys):
    code, out, err = run_cli(capsys)
    assert code == 0 and err == ""
    assert "bound, eccentricity e = 0.5000" in out
    assert "semi-major axis  100.0 GM/c²  = 1477 km" in out
    assert "periapsis        50.00 GM/c²  = 738.3 km" in out
    assert "period           6283 GM/c³  = 309.5 ms" in out
    assert len(event_rows(out, "apoapsis")) == 1
    assert "reached the end time" in out


def test_several_orbits_around_sagittarius_a(capsys):
    code, out, _err = run_cli(capsys, "--orbits", "3", "--mass", "4.3e6")
    assert code == 0
    assert "semi-major axis  100.0 GM/c²  = 4.244 AU" in out
    assert "period           6283 GM/c³  = 1.540 d" in out
    assert len(event_rows(out, "apoapsis")) == 3


def test_free_fall_stops_at_the_requested_radius(capsys):
    code, out, _err = run_cli(capsys, "--x", "10", "--vy", "0", "--stop-radius", "2")
    assert code == 0
    assert "stopped at r = 2, t = 33.70 GM/c³" in out


def test_an_unbound_orbit_runs_for_a_given_duration(capsys):
    code, out, _err = run_cli(capsys, "--vy", "0.25", "--duration", "2000")
    assert code == 0
    assert "unbound" in out and "period           ∞" in out


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--x", "0"), "infinite at r = 0"),
        (("--vy", "0.25"), "has no period"),
        (("--rtol", "1e-15"), "rtol"),
        (("--orbits", "0"), "--orbits"),
        (("--mass", "-1"), "mass"),
        (("--stop-radius", "-2"), "radius"),
        (("--vx", "nan"), "finite"),
    ],
)
def test_invalid_input_is_reported_and_nothing_is_run(capsys, arguments, message):
    code, out, err = run_cli(capsys, *arguments)
    assert code == 2
    assert out == ""
    assert message in err


def test_runs_as_a_module_and_survives_redirected_output():
    """As a user would start it. The output is piped, which on Windows used to need UTF-8."""
    result = subprocess.run(
        [sys.executable, "-m", "bhlab.orbit", "--mass", "6.5e9"], capture_output=True
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert "6.500 × 10⁹ M☉" in result.stdout.decode("utf-8")

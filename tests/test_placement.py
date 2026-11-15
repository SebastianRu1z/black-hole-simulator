"""The rule that turns a dragged arrow into a velocity, and the preview of the orbit it makes."""

import math

import pytest

from bhlab.physics.newtonian import circular_velocity
from bhlab.simulation.model import Simulation
from bhlab.simulation.placement import drag_velocity, preview


@pytest.mark.parametrize("r", [3.0, 10.0, 250.0])
def test_a_sideways_arrow_as_long_as_r_gives_the_circular_velocity(r):
    """v = d / r^(3/2) and |d| = r give |v| = √(1/r), at right angles to the radius."""
    vx, vy = drag_velocity(r, 0.0, 0.0, r)
    assert (vx, vy) == pytest.approx(circular_velocity(r, 0.0), rel=1e-15)
    elements = preview(Simulation(), r, 0.0, vx, vy).elements
    assert elements.eccentricity == pytest.approx(0.0, abs=1e-12)


def test_an_arrow_root_two_times_longer_gives_the_escape_speed():
    vx, vy = drag_velocity(10.0, 0.0, 0.0, math.sqrt(2.0) * 10.0)
    assert math.hypot(vx, vy) == pytest.approx(math.sqrt(2.0 / 10.0), rel=1e-15)
    # E = v²/2 − 1/r = 0 exactly in theory; in floating point it lands within rounding of zero,
    # on either side, so the label (bound, parabolic or unbound) is not a stable thing to test.
    assert preview(Simulation(), 10.0, 0.0, vx, vy).elements.energy == pytest.approx(0.0, abs=1e-15)


def test_the_velocity_scales_as_the_arrow_divided_by_r_to_the_three_halves():
    # At r = 5 (from x = 3, y = 4): scale = 5^(-3/2) = 0.0894427…
    assert drag_velocity(3.0, 4.0, 2.0, -1.0) == pytest.approx(
        (2.0 * 5.0**-1.5, -1.0 * 5.0**-1.5), rel=1e-15
    )
    assert drag_velocity(3.0, 4.0, 0.0, 0.0) == (0.0, 0.0)


@pytest.mark.parametrize(
    ("x", "y", "dx", "dy"),
    [(0.0, 0.0, 1.0, 0.0), (math.nan, 1.0, 0.0, 0.0), (5.0, 0.0, math.inf, 0.0)],
)
def test_drag_velocity_refuses_the_centre_and_non_finite_values(x, y, dx, dy):
    with pytest.raises(ValueError):
        drag_velocity(x, y, dx, dy)


def test_preview_agrees_with_what_adding_would_do():
    simulation = Simulation()
    inside = preview(simulation, 1.5, 0.0, 0.0, 0.5)
    too_fast = preview(simulation, 10.0, 0.0, 0.0, 1.0)
    assert not inside.is_valid and "start outside r = 2" in inside.error
    assert not too_fast.is_valid and "slower than light" in too_fast.error
    for invalid in (inside, too_fast):
        with pytest.raises(ValueError, match=invalid.error[:20]):
            simulation.add_particle(invalid.x, invalid.y, invalid.vx, invalid.vy)
    assert len(simulation) == 0  # the preview itself adds nothing


def test_preview_of_a_bound_ellipse():
    # Periapsis 50 of the a = 100, e = 0.5 ellipse: v² = 2/50 − 1/100 = 0.03.
    placement = preview(Simulation(), 50.0, 0.0, 0.0, math.sqrt(0.03))
    assert placement.is_valid and not placement.reaches_stop_radius
    assert placement.elements.kind == "bound"
    assert placement.elements.apoapsis == pytest.approx(150.0, rel=1e-12)
    assert placement.speed_over_circular == pytest.approx(math.sqrt(0.03 * 50.0), rel=1e-12)


@pytest.mark.parametrize(
    ("state", "reaches"),
    [
        ((10.0, 0.0, 0.0, 0.0), True),  # at rest: falls straight in
        ((10.0, 0.0, 0.0, 0.05), True),  # bound, periapsis L²/(1 + e) = 0.25/1.975 ≈ 0.13 < 2
        ((10.0, 0.0, 0.0, 0.2), False),  # bound, periapsis 4/1.6 = 2.5 > 2
        ((10.0, 0.0, -0.6, 0.0), True),  # unbound but heading straight in
        ((10.0, 0.0, 0.6, 0.0), False),  # unbound and heading straight out: never comes back
    ],
)
def test_preview_says_whether_the_particle_will_come_down_to_the_stop_radius(state, reaches):
    placement = preview(Simulation(), *state)
    assert placement.reaches_stop_radius is reaches
    elements = placement.elements
    if elements.kind == "bound":
        assert reaches == (elements.periapsis <= 2.0)


def test_removing_a_particle_never_reuses_its_number():
    simulation = Simulation()
    first = simulation.add_particle(10.0, 0.0, 0.0, 0.3)
    second = simulation.add_particle(20.0, 0.0, 0.0, 0.2)
    simulation.remove_particle(first.id)
    third = simulation.add_particle(30.0, 0.0, 0.0, 0.18)
    assert [p.id for p in simulation.particles] == [second.id, third.id] == [1, 2]
    with pytest.raises(KeyError):
        simulation.remove_particle(first.id)


def test_removed_particles_stay_removed_after_a_reset_and_the_rest_keep_moving():
    simulation = Simulation()
    simulation.add_particle(10.0, 0.0, *circular_velocity(10.0, 0.0))
    simulation.add_particle(20.0, 0.0, *circular_velocity(20.0, 0.0))
    simulation.advance(50.0)
    simulation.remove_particle(0)
    simulation.advance(50.0)
    simulation.reset()
    assert [p.id for p in simulation.particles] == [1]
    assert tuple(simulation.particles[0].state) == (20.0, 0.0, *circular_velocity(20.0, 0.0))

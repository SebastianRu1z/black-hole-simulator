# Learning notes — Black Hole Physics Lab

A growing technical reference for understanding this project: the physics, the mathematics, the
Python and the engineering ideas behind the code. It is organised by topic, not by date. Each
entry names the checkpoint that introduced it, and every new checkpoint adds to the sections below.

Last updated: 2026-11-12, Checkpoint 1C-2. Covered so far: 1A (units, constants, the window), 1B (the
2D map), 1C-1 (equations of motion, RK4, velocity Verlet) and 1C-2 (adaptive DOP853, events, orbital
elements, the `python -m bhlab.orbit` command). Orbits are computed and tested, but not yet shown in
the window; that is Checkpoint 1D.

File paths in this document are relative to `src/bhlab/` unless they start with `tests/`.

## 1. Physics

### 1.1 One length sets the size of a black hole (1A)

A non-rotating black hole is described by a single number, its mass M. The mass only ever appears
in the product GM, and from GM and the speed of light c there is exactly one way to build a length
and one way to build a time:

    r_g = GM / c²      the gravitational radius
    t_g = GM / c³      the time light needs to travel r_g

Check the units: GM is measured in m³/s². Dividing by c² (m²/s²) leaves metres. Dividing by c³
(m³/s³) leaves seconds.

Worked example, the Sun: GM☉ = 1.327 124 4 × 10²⁰ m³/s² and c² = 8.987 55 × 10¹⁶ m²/s², so
r_g = 1476.6 m and t_g = r_g / c = 4.925 µs. Every other black hole follows by multiplying with its
mass in solar masses:

| Black hole | Mass | r_g | t_g |
|---|---|---|---|
| Stellar-mass | 10 M☉ | 14.77 km | 49.25 µs |
| Sagittarius A* | 4.3 × 10⁶ M☉ | 6.349 × 10⁶ km = 0.04244 AU | 21.18 s |
| M87* | 6.5 × 10⁹ M☉ | 64.16 AU | 8.893 h |

In code: `BlackHole.length_unit` and `BlackHole.time_unit` in `units.py`.

### 1.2 Geometrized units: G = c = 1 (1A)

The program measures every length in units of r_g and every time in units of t_g. In these units
G = c = 1 and the mass has disappeared from the equations. One calculation then describes a black
hole of any mass, and SI values are obtained at the very end by multiplying with r_g or t_g
(`BlackHole.length_to_si`, `BlackHole.time_to_si`).

This is why the map in the window does not change when you change the mass. Only the scale bar
changes, because it is the one place where r_g is turned back into kilometres.

### 1.3 Three radii to know (1A, drawn in 1B)

For a non-rotating (Schwarzschild) black hole, in units of r_g:

| Radius | Value | Meaning |
|---|---|---|
| Event horizon, r_s | 2 | Nothing that crosses it can come back out, not even light |
| Photon sphere, r_ph | 3 | Light can circle the black hole here, on an unstable orbit |
| ISCO, r_ISCO | 6 | The innermost stable circular orbit for matter |

Status: the program states these values; it does not derive them yet. Deriving them from the
equations of motion is part of Stage 2. Newtonian gravity, which Stage 1 uses, has none of the
three: in Newton's theory a circular orbit exists at every radius.

### 1.4 Why the code stores GM and not M (1A)

Tracking of planets and spacecraft measures the product GM of the Sun to better than one part in a
billion. G on its own is known to about two parts in 100 000. Lengths and times need only GM, so
the program converts solar masses with GM☉ and never touches G. G is used only to print a mass in
kilograms. The lesson is general: carry the best-measured quantity through a calculation.

### 1.5 What the map is, and what it is not (1B)

The map shows the orbital plane from above in Schwarzschild coordinates, in which a circle of
radius r has circumference 2πr. It is not a photograph. Light bends near a black hole, so a camera
would see a dark shadow of radius 3√3 r_g ≈ 5.2 r_g, about 2.6 times the horizon. Images belong to
Stage 6.

### 1.6 Newtonian orbits (1C-1)

A test particle (one too light to move the black hole) obeys Newton's law of gravitation:

    d²r/dt² = −GM r / |r|³      becomes      d²r/dt² = −r / |r|³   with GM = 1

The acceleration points at the mass and has size 1/r². Two quantities stay constant along any orbit,
per unit mass of the particle:

    energy             E = v²/2 − 1/r       negative for a bound orbit, E = −1/(2a)
    angular momentum   L = x v_y − y vₓ     positive for anticlockwise motion

Useful results for checking the program (all with GM = 1):

| Result | Formula | Example, a = r = 100 |
|---|---|---|
| Circular speed | v = √(1/r) | 0.1 c |
| Kepler's third law | T = 2π a^(3/2) | 6283 GM/c³ = 0.3095 s for 10 M☉, 1.54 days for Sgr A* |
| Vis-viva equation | v² = 2/r − 1/a | at periapsis r = 50 of an a = 100 orbit: v = √0.03 = 0.1732 c |
| Ellipse | periapsis a(1 − e), apoapsis a(1 + e) | e = 0.5: 50 and 150 |

Code: `physics/newtonian.py`. The model is wrong close to a black hole. It has no horizon and no
ISCO, and at r = 100 the particle already moves at a tenth of the speed of light. It is the starting
point that general relativity corrects in Stage 2.

### 1.7 Orbital elements: every Newtonian orbit is a conic (1C-2)

Under 1/r² gravity every orbit is a conic section with the mass at one focus: an ellipse (a circle
is the special case e = 0), a parabola or a hyperbola. One position and one velocity fix it
completely, because three quantities are constant along it (GM = 1):

    energy               E = v²/2 − 1/r
    angular momentum     L = x v_y − y vₓ
    eccentricity vector  e = (v² − 1/r) r − (r·v) v      points at periapsis, length e

| Element | Formula | Bound (E < 0) | Parabolic (E = 0) | Unbound (E > 0) |
|---|---|---|---|---|
| eccentricity | \|e\| | 0 ≤ e < 1 | 1 | e > 1 |
| semi-major axis | a = −1/(2E) | positive | ∞ | negative |
| periapsis | r_p = L²/(1 + e) | yes | yes | yes |
| apoapsis | r_a = a(1 + e) | yes | ∞ | ∞ |
| period | T = 2π a^(3/2) | yes | ∞ | ∞ |

Worked example, a state between periapsis and apoapsis: (x, y) = (−50, 86.60), (vₓ, v_y) = (−0.1, 0).

- r = 100, v² = 0.01, r·v = 5.
- E = 0.005 − 0.01 = −0.005, so a = 100.
- e = (0.01 − 0.01)·r − 5·(−0.1, 0) = (0.5, 0), so e = 0.5 and periapsis lies along +x.

A fall from rest is the extreme case: L = 0, e = 1, a flattened ellipse that runs straight into
the mass. Code: `physics/orbital_elements.py`.

## 2. Mathematics

### 2.1 Significant figures and scientific notation (1A)

`format_number` in `formatting.py` writes a number with four significant figures. It writes the
number as m × 10ᵉ with 1 ≤ |m| < 10, then uses plain decimals when −2 ≤ e < 5 and the form
`1.270 × 10⁷` otherwise. The order matters: it rounds first and chooses the notation afterwards, so
99 999.6 becomes 1.000 × 10⁵ and not 10.000 × 10⁴.

### 2.2 Logarithmic scales (1A)

Black hole masses span eleven powers of ten, so the mass slider is logarithmic: slider position p
stands for the mass M = 10^(p/100) solar masses. Equal steps of the slider multiply the mass by
the same factor, 10^0.01 ≈ 1.023. A linear slider from 1 to 10¹¹ would put every stellar-mass black
hole in its first pixel.

### 2.3 Round numbers: the 1-2-5 rule (1B)

A scale bar should have a round length. `nice_length(maximum)` in `ui/scale_bar.py` returns the
largest number of the form 1, 2 or 5 × 10ⁿ that does not exceed `maximum`:

    n = floor(log10(maximum))        the power of ten
    f = maximum / 10ⁿ                a number from 1 to 10
    step = 5 if f ≥ 5, 2 if f ≥ 2, otherwise 1
    result = step × 10ⁿ

Example: the view is 20.7 r_g wide and the bar may use a quarter of it, 5.19 r_g. Then n = 0,
f = 5.19 and the bar is 5 r_g long. Oscilloscopes use the same 1-2-5 sequence for their
volts-per-division settings.

### 2.4 Cartesian and polar coordinates (1B)

The cursor readout converts the map position (x, y) to a radius and an angle:

    r = √(x² + y²)                   math.hypot(x, y)
    φ = atan2(y, x), shown from 0° to 360°

`atan2(y, x)` is used instead of `atan(y / x)` because it finds the quadrant from the two signs and
does not divide by zero on the y axis. Example: (3, 4) gives r = 5 and φ = 53.1°. In code:
`describe_cursor` in `ui/main_window.py`.

### 2.5 From map coordinates to pixels (1B)

The camera is a linear map between r_g and pixels. One scale s, in pixels per r_g, serves both
directions, so circles stay circles (the aspect ratio is locked):

    x_pixel = s · (x − x_left)            y_pixel = s · (y_top − y)

- Panning changes x_left and y_top and leaves s alone.
- Zooming by a factor k replaces s with k · s. Zooming about the cursor keeps the map point under
  the cursor where it is, while everything else moves towards it or away from it.
- With a map area of W by H pixels showing a region Δx by Δy, s = W / Δx = H / Δy. If W changes,
  then Δx or s has to change with it. That was the defect fixed at the end of 1B: the plotting
  library let the left axis grow with its tick labels, which made W smaller while you panned.

### 2.6 Floating-point numbers (1A, 1B)

Python's `float` is a 64-bit binary number with 53 bits of precision, about 16 decimal digits.

- Every whole number up to 2⁵³ ≈ 9.007 × 10¹⁵ is stored exactly. Above that the stored values are
  2 apart, then 4, and so on. The light-year, 9 460 730 472 580 800 m, is larger than 2⁵³ but is a
  multiple of 64, so it is still exact (`tests/test_constants.py` checks this).
- Most decimal fractions are not exact: `0.1 + 0.2 == 0.3` is `False`. Tests therefore compare with
  a tolerance, `pytest.approx`, and use `==` only where exactness can be argued.
- Subtracting two nearly equal numbers loses digits. Near x = 10⁶ neighbouring floats are
  1.2 × 10⁻¹⁰ apart, so a difference of 0.03 between two such numbers is good to only 4 parts in
  10⁹. One of the map tests reads the scale in this way and allows for it. That is a numerical
  error: the scale itself had not changed.

### 2.7 From a second-order equation to a first-order system (1C-1)

Numerical solvers expect dy/dt = f(t, y), with only first derivatives. A second-order equation is
rewritten by treating the velocity as an unknown of its own. With the state y = (x, y, vₓ, v_y):

    dx/dt = vₓ      dy/dt = v_y      dvₓ/dt = aₓ(x, y)      dv_y/dt = a_y(x, y)

Two second-order equations become four first-order ones. This is the state-space form used in
control engineering, with the state vector holding positions and velocities instead of capacitor
voltages and inductor currents. In code: `first_order_system` in `solvers/fixed_step.py`.

### 2.8 Runge–Kutta 4 (1C-1)

Euler's method, y(t + h) ≈ y + h f(t, y), follows the slope at the start of the step all the way to
its end. On an orbit it spirals outward, because every step leaves the circle along the tangent.
RK4 samples the slope four times and averages them with weights 1, 2, 2, 1:

    k₁ = f(t, y),   k₂ = f(t + h/2, y + h k₁/2),   k₃ = f(t + h/2, y + h k₂/2),   k₄ = f(t + h, y + h k₃)
    y(t + h) ≈ y + h (k₁ + 2k₂ + 2k₃ + k₄) / 6

Two checks show the idea:
- For dy/dt = y, one step reproduces e^h = 1 + h + h²/2 + h³/6 + h⁴/24 + … up to the h⁴ term.
- For dy/dt = g(t), RK4 becomes Simpson's rule, which integrates cubics exactly.

### 2.9 Velocity Verlet and symplectic integrators (1C-1)

    v_half = v + (h/2) a(x)          a half kick
    x_new  = x + h v_half             a full drift
    v_new  = v_half + (h/2) a(x_new)  another half kick

It costs one force evaluation per step instead of four, and it is only second order. It is
*symplectic*: each step is an exact motion of a slightly different mechanical system, close to the
real one. Three consequences, all measured by the tests:
- The energy error oscillates but does not grow, even over thousands of orbits.
- For a central force, the angular momentum is conserved exactly. Each kick changes v along x, and
  x × x = 0; each drift changes x along v, and v × v = 0.
- At the same step size its energy error can be larger than RK4's (2.7 × 10⁻³ against 2.5 × 10⁻⁶
  for the test ellipse at 200 steps per orbit). It wins over long times, not per step.

### 2.10 Order of convergence, and the two kinds of error (1C-1)

A method has order p if its error after a fixed time behaves like C·hᵖ. Halving h then divides the
error by 2ᵖ: 16 for RK4, 4 for Verlet. The program measured 16.65 and 4.00, so p = log₂(ratio)
gives 4.06 and 2.00. Measuring the order is the standard test that an integrator is implemented
correctly: a wrong coefficient usually drops the order.

| Kind of error | Example | Cure |
|---|---|---|
| Numerical error | energy drifting in an RK4 run | smaller step, better method |
| Model (physical) error | Newton's theory near a black hole | a better theory (general relativity) |
| Round-off error | about 10⁻¹⁶ relative per operation | rarely matters here; it limits how small a useful h can be |

A smaller step never fixes a model error. A perfect solution of the Newtonian equations is still a
wrong description of an orbit at 10 r_g.

### 2.11 Adaptive step size (1C-2)

A fixed step must suit the hardest part of the orbit. On the e = 0.9 ellipse the particle passes
periapsis at r = 10 about 360 times faster in angle than it turns at apoapsis, so a fixed step
wastes work almost everywhere. An adaptive method chooses each step itself:

1. Take a step of length h with two formulas of different order that share their slope samples.
   DOP853 has an 8th-order result and lower-order companions.
2. Their difference estimates the error of the step, err.
3. Accept the step if err ≤ atol + rtol·|y|. Otherwise reject it and retry with a smaller h.
4. Choose the next step as roughly h·(tolerance/err)^(1/8) with a safety factor: larger when the
   step was easy, smaller when it was hard.

Measured at e = 0.9 over one orbit:

| Method | Force evaluations | End error (GM/c²) |
|---|---|---|
| RK4, 1000 steps | 4 000 | 1.8 |
| RK4, 4000 steps | 16 000 | 4.7 × 10⁻³ |
| DOP853, rtol = 10⁻¹⁰ | 1 334 | 1.2 × 10⁻⁶ |

Two cautions. The tolerance limits the error of each step, not the error at the end of a long run.
And a tolerance cannot go below about 10⁻¹⁴ in double precision; the program refuses rtol < 10⁻¹³
instead of letting SciPy quietly raise it.

### 2.12 Events: finding when something happens (1C-2)

An event is a zero crossing of a function g(t, y) of the motion:

| Event | g(t, y) | Crossing direction |
|---|---|---|
| periapsis | r·v = x vₓ + y v_y | negative to positive (stops approaching) |
| apoapsis | r·v | positive to negative (stops receding) |
| reaching radius R | √(x² + y²) − R | either, or one chosen direction |

After each step the solver compares the sign of g at both ends. If it changed, it finds the crossing
inside the step with a root finder (Brent's method), using a polynomial that interpolates the
solution between the step's end points. That is why event times are far more precise than the step
length: about 10⁻⁹ of a period here, with steps of several percent of a period.

### 2.13 Exact solutions used as benchmarks (1C-2)

**Kepler's equation** gives the time to reach any point of an ellipse. With the eccentric anomaly E
(an angle, not the energy):

    r = a(1 − e cos E)          t = √(a³) (E − e sin E)    (time since periapsis, GM = 1)

Example: when does the a = 100, e = 0.5 orbit first reach r = 100? cos E = 0, so E = π/2 and
t = 1000·(π/2 − 0.5) = 1070.80 GM/c³. The program's event: 1070.80, agreeing to 10⁻⁹.

**Free fall from rest** at r₀, with the angle η running from 0:

    r = r₀ cos²η          t = √(r₀³/2) (η + sin η cos η)

From r₀ = 10 to r = 2: cos²η = 0.2, η = 1.107, t = 33.70 GM/c³, which is 1.66 ms for 10 M☉. The program
stops at 33.70, agreeing to 4 × 10⁻¹².

## 3. Python

### 3.1 How the project is laid out (1A)

| Path | Role |
|---|---|
| `constants.py`, `units.py`, `formatting.py` | The physics side: numbers and text, no graphics |
| `ui/` | The window: one module per panel or widget |
| `__main__.py` | Lets `python -m bhlab` start the application |
| `tests/` | One test file per subject, run with pytest |
| `pyproject.toml` (project root) | Name, dependencies and tool settings of the package |

The rule that shapes everything: the interface may import the physics, never the reverse. The
physics can then be tested and reused without a window. `tests/test_architecture.py` enforces it
by importing the physics modules in a fresh Python process and checking that Qt was not loaded.

### 3.2 A class that is a value: the frozen dataclass (1A)

Abridged from `units.py`:

```python
@dataclass(frozen=True, slots=True)
class BlackHole:
    gm: float

    def __post_init__(self) -> None:
        _require_positive_finite(self.gm, "The gravitational parameter GM")

    @classmethod
    def from_solar_masses(cls, solar_masses: float) -> Self:
        return cls(gm=solar_masses * GM_SUN)

    @property
    def length_unit(self) -> float:
        return self.gm / C**2
```

- `@dataclass` writes the constructor from the list of fields.
- `frozen=True` makes the object immutable. A black hole of 10 M☉ can never quietly become one of
  11 M☉; a new mass means a new object. Bugs caused by shared, changing state cannot happen.
- `__post_init__` runs after construction and rejects invalid values with a clear message.
- `@classmethod` gives a second way to build the object, named after what you have in hand.
- `@property` makes a computed value read like a stored one: `bh.length_unit`, without brackets.

### 3.3 Reject bad input, never repair it (1A)

`parse_mass_text` in `ui/mass_controls.py` turns typed text into a mass or raises `ValueError` with
a sentence written for the user. It refuses "4,3" instead of guessing what the comma means. A
scientific program that quietly "corrects" its input produces results nobody asked for.

### 3.4 Event-driven programs: signals and slots (1A, 1B)

A graphical program does not run from top to bottom. After `app.exec()` it waits in the event loop
and reacts to events: a key press, a mouse move, a timer. Qt connects the parts with signals and
slots:

```python
class MassControls(QWidget):
    mass_changed = Signal(float)              # announces: "there is a new mass"
    ...
        self.mass_changed.emit(mass)          # sent when a valid mass is applied

# in MainWindow.__init__: who reacts
self.controls.mass_changed.connect(self._on_mass_changed)
```

The sender does not know who is listening. That keeps the mass panel, the scales table and the map
independent of each other. Follow one chain to see it work: typing a mass and pressing Enter runs
`_on_editing_finished`, which calls `parse_mass_text` and then `_apply`, which emits
`mass_changed`. `MainWindow._on_mass_changed` builds a new `BlackHole` and hands it to the table and
to the map.

A trap worth remembering, from the preset buttons:

```python
button.clicked.connect(lambda _checked=False, m=preset.solar_masses: self.set_mass(m))
```

The default `m=preset.solar_masses` captures the value when the lambda is created. Written as
`lambda: self.set_mass(preset.solar_masses)` inside the loop, all three buttons would use the last
preset, because the name `preset` is only looked up when a button is clicked.

### 3.5 Building on a library (1B)

The map is a `pyqtgraph.PlotWidget`. The project configures it instead of drawing axes by hand:
`setAspectLocked` for equal scales, `setLimits` for the zoom and pan limits, `setStyle` for the
axes. The price of a library is its defaults. pyqtgraph sized the left axis to its labels, which is
wrong for a map, and the cure was two settings (`autoExpandTextSpace=False` and a fixed
`tickTextWidth`), found by reading the library's source code.

### 3.6 Testing with pytest (1A, 1B)

- A test is a function whose name starts with `test_` and that uses `assert`.
- `@pytest.mark.parametrize` runs one test over a table of inputs and expected outputs.
- `pytest.approx(value, rel=...)` compares floats with a tolerance.
- `pytest.raises(ValueError)` checks that bad input is refused.
- A fixture (`qapp` and `window` in `tests/conftest.py`) prepares something several tests need.
- Interface tests run on Qt's "offscreen" platform, so no window appears.
- Test at the boundaries: `format_length_auto` is tested exactly at 0.01 AU and just below it.
- Write the test first when fixing a defect. The pan tests were written before the fix, failed
  (eight of them), and passed after it. A test that has never failed has not shown that it can.
- Read what a passing test asserts. The earlier drag test passed only because its tolerance had
  been widened to 1 %.

### 3.7 NumPy arrays (1C-1)

A NumPy array is a block of numbers of one type, and arithmetic applies to every element at once:

```python
y = np.array([100.0, 0.0, 0.0, 0.1])  # x, y, vx, vy
y + 0.5 * k1  # element by element, no loop
states = np.empty((n + 1, 4))  # a table: one row per time step
states[:, 0]  # the whole x column
```

This is why `rk4_step` reads almost like the formula. Two habits from this checkpoint:
- `states.flags.writeable = False` makes a finished result read-only, so nothing can change it by
  accident. It is the array version of the frozen dataclass.
- `np.hypot(x, y)` and friends work on whole columns: `np.hypot(states[:, 0], states[:, 1])` gives
  the radius at every step.

### 3.8 Functions as values, and closures (1C-1)

The solvers do not know about gravity. They receive the force law as a function argument:

```python
integrate(acceleration, start, step, n_steps, "rk4")  # gravity
integrate(lambda x: -x, start, 0.2, 20_000, "verlet")  # a spring, or an LC tank
```

`first_order_system(acceleration)` builds and *returns* a new function `f(t, y)`. The inner function
remembers the `acceleration` it was made from, even after `first_order_system` has returned. That is
a closure. It lets one RK4 routine solve any equation of the form d²x/dt² = a(x).

### 3.9 Tests that are allowed to fail (1C-1)

Every tolerance in `tests/test_fixed_step.py` comes from a measurement plus a margin, and the comment
next to it says what was measured. To check that the tests can catch mistakes, the RK4 weights were
changed to 1, 1, 3, 1 in a temporary copy: 7 tests failed. Breaking the Verlet velocity update made 5
fail. A test suite that would pass whatever the code did is worse than none, because it gives false
confidence.

### 3.10 Using a library's interface: SciPy (1C-2)

`solve_ivp(f, (t0, t1), y0, method="DOP853", rtol=..., atol=..., events=[...])` is the call the
program wraps. Two things about it are worth knowing.

SciPy reads event settings from *attributes of the event function*. In Python a function is an
object, so it can carry data:

```python
def event(t, y):
    return spec.function(t, y)


event.terminal = spec.terminal  # stop the run at this event?
event.direction = spec.direction  # +1, −1 or 0
```

The program wraps SciPy instead of calling it everywhere. The wrapper (`integrate_adaptive`) checks
the input, removes the false event at t = 0, refuses settings SciPy would quietly change, and
returns read-only results in the project's own types. The rest of the code then never depends on
SciPy's quirks.

### 3.11 Values that may be missing: None and ∞ (1C-2)

A circular orbit has no periapsis direction, so `periapsis_angle` has the type `float | None` and is
`None` there. Code that uses it must check first, as the command line does. Quantities that exist but
are infinite, such as the period of an escaping orbit, are `math.inf` instead. That is a real value
in the mathematics, and `math.isinf` tests for it.

### 3.12 A command-line program (1C-2)

`src/bhlab/orbit.py` uses `argparse`: each `add_argument` declares an option, its type, its default
and its help text, and `--help` is generated from them. Other points:
- `main(argv)` returns an exit code: 0 for success, 2 for invalid input. Scripts and other programs
  read it to know whether the run worked.
- Errors go to `sys.stderr` and results to `sys.stdout`, so a redirected result file stays clean.
- `if __name__ == "__main__":` runs only when the file is started as a program
  (`python -m bhlab.orbit`), not when the tests import `main`.
- On Windows, output redirected to a file uses an old code page that cannot write M☉ or GM/c³. The
  program switches its output to UTF-8 when it starts. A test runs it as a separate process with
  piped output to catch this.

## 4. Key functions

| Function | File | Takes | Gives |
|---|---|---|---|
| `BlackHole.from_solar_masses` | `units.py` | mass in M☉ | a `BlackHole` |
| `BlackHole.length_to_si` | `units.py` | length in r_g | metres |
| `format_number` | `formatting.py` | a number, significant figures | text such as `1.270 × 10⁷` |
| `format_length_auto` | `formatting.py` | metres | text in mm, m, km, AU or ly |
| `parse_mass_text` | `ui/mass_controls.py` | typed text | mass in M☉, or a `ValueError` |
| `nice_length` | `ui/scale_bar.py` | a maximum length | the largest 1-2-5 number not above it |
| `ScaleBar.update_scale` | `ui/scale_bar.py` | pixels per r_g, view width, black hole | sets the bar and its label |
| `describe_cursor` | `ui/main_window.py` | x and y in r_g, black hole | the readout text |
| `BlackHoleView.zoom_by` | `ui/viewport.py` | zoom factor | moves the camera |
| `BlackHoleView.pixels_per_unit` | `ui/viewport.py` | nothing | the scale s, in pixels per r_g |
| `acceleration` | `physics/newtonian.py` | position (x, y) | −r/r³ as an array; refuses r = 0 |
| `specific_energy`, `specific_angular_momentum` | `physics/newtonian.py` | a state (x, y, vₓ, v_y) | E and L |
| `circular_orbit` | `physics/newtonian.py` | radius r | the state (r, 0, 0, √(1/r)) |
| `kepler_period` | `physics/newtonian.py` | semi-major axis a | 2π a^(3/2) |
| `rk4_step` | `solvers/fixed_step.py` | f, t, y, h | y at t + h |
| `velocity_verlet_step` | `solvers/fixed_step.py` | force law, x, v, a, h | new x, v and a |
| `integrate` | `solvers/fixed_step.py` | force law, start state, h, number of steps, method | a read-only `Trajectory` |
| `orbital_elements` | `physics/orbital_elements.py` | a state | kind, E, L, e, a, periapsis, apoapsis, period, periapsis angle |
| `integrate_adaptive` | `solvers/adaptive.py` | force law, start state, duration, rtol, atol, events | an `AdaptiveTrajectory` with steps, events and why it stopped |
| `periapsis`, `apoapsis`, `radius_reached` | `solvers/adaptive.py` | (a radius, a direction, whether to stop) | an `EventSpec` to watch for |
| `main` | `orbit.py` | command-line arguments | prints the orbit and its events; returns 0 or 2 |

`format_length_auto` without its docstring, as an example of a rule written as code:

```python
def format_length_auto(metres: float, sig: int = 4) -> str:
    size = abs(metres)
    if size >= 0.1 * LIGHT_YEAR:
        return f"{format_number(metres / LIGHT_YEAR, sig)} ly"
    if size >= 0.01 * AU:
        return f"{format_number(metres / AU, sig)} AU"
    return format_length_si(metres, sig)
```

The largest unit is tried first. `abs` is used for the decision and the signed value for the text,
so a coordinate of −1 AU prints as "-1.000 AU".

## 5. Electrical-engineering connections

Only connections that are real are listed here.

- **Normalisation.** Geometrized units do for black holes what a normalised prototype does for
  filters: design once for 1 Ω and 1 rad/s, then scale to the impedance and frequency you need.
  Here the calculation is done once for r_g = 1 and then scaled to the mass. Normalised frequency in
  DSP and the per-unit system in power engineering are the same idea.
- **Logarithmic scales.** The mass slider covers eleven decades the way a Bode plot covers
  frequency, and for the same reason: equal ratios deserve equal space.
- **Event-driven design.** Signals and slots resemble interrupt-driven firmware: a source raises an
  event and handlers respond, with no polling loop and no knowledge of each other.
- **Instrument calibration.** A scale bar is a graticule. Its calibration must not depend on where
  you look, which is why the map area was given a fixed size.
- **Finite word length.** A 64-bit float has a 53-bit mantissa, as a converter has a fixed number of
  bits. Round-off and the loss of digits in subtraction are the effects that also limit fixed-point
  filters.
- **The LC tank (1C-1).** An ideal LC circuit obeys d²q/dt² = −q/(LC), the same equation as
  d²x/dt² = −x in the test of the two integrators. RK4 loses a little energy every step, as if a small
  resistor were in the circuit: after 640 periods at h = 0.2 the energy has fallen from 0.5 to 0.4912.
  Verlet keeps it between 0.495 and 0.5 indefinitely. A circuit simulator that damps a lossless tank
  is showing you its integrator, not your circuit.
- **SPICE (1C-1).** A transient analysis solves the circuit's state equations step by step, exactly as
  `integrate` does for an orbit. SPICE uses implicit methods (trapezoidal, Gear) and adjusts the step
  to an error tolerance, which is where Checkpoint 1C-2 goes with DOP853.
- **Step size as sampling (1C-1).** A step of h samples the motion h apart. Too coarse a step gives
  wrong answers or unstable growth, much as too low a sample rate does in a digital filter. At 250
  steps per orbit Verlet already misses the start point by 2.8 r_g after one orbit.
- **RELTOL and ABSTOL (1C-2).** SPICE accepts a transient time step when its estimated local error is
  below RELTOL·|value| + ABSTOL, and otherwise cuts the step. `integrate_adaptive` does the same with
  rtol and atol. Fast edges in a circuit play the part of periapsis in an orbit: that is where both
  programs take small steps.
- **Zero-crossing detection (1C-2).** Events work like an oscilloscope trigger or a comparator. A
  signal (here r·v) is watched for a crossing of zero in a chosen direction, the rising or falling
  edge, and the crossing time is then located far more finely than the sampling interval, as a
  digital oscilloscope interpolates between samples.
- **Not built yet.** Time dilation as a frequency shift, signal paths along light rays, spectra and
  link budgets come in Stages 3 and 5.

## 6. Experiments

Predict first, then start the program with `.venv\Scripts\python.exe -m bhlab` and check.

1. Press "Reset view", then click the three presets in turn. Prediction: the circles do not move at
   all, and the scale bar reads 5 r_g = 73.83 km, then 0.2122 AU, then 320.8 AU.
2. Which mass has a gravitational radius of exactly 1 AU? M = 1 AU / 1476.625 m ≈ 1.0131 × 10⁸ M☉.
   Type `1.0131e8` and read the "Gravitational radius" row.
3. Move the cursor along the ISCO circle. Prediction: r stays close to 6 r_g while φ runs from 0° to
   360°. At the point (3, 4) the readout says r = 5.000 r_g and φ = 53.1°.
4. Click the handle of the mass slider, then press the right-arrow key once. Prediction: the mass
   goes from 10 to 10.2 M☉, the factor 10^0.01 ≈ 1.023 rounded to three figures.
5. Choose M87* and zoom out until the scale bar reads 1000 r_g. Prediction: it says 1.015 ly. The
   unit has changed from AU to light-years on its own.
6. In a Python prompt (`.venv\Scripts\python.exe`), run
   `from bhlab.units import BlackHole` and then `BlackHole.from_solar_masses(1).length_unit`.
   Prediction: 1476.625… metres. Then try a mass of `-1` and read the error message.
7. Break something on purpose. In `ui/viewport.py` change `_WIDEST_TICK_LABEL` to `"-8"` and run the
   tests. Prediction: exactly one test fails, the one that checks the labels fit, while the tests
   for a constant map size still pass. Then change it back.
8. Floating point, in a Python prompt: `0.1 + 0.2 == 0.3`, then `float(2**53 + 1) == 2**53 + 1`.
   Both are `False`. Explain each to yourself with section 2.6.

9. Run `.venv\Scripts\python.exe examples\integrator_comparison.py`. Prediction: the "ratio" column
   approaches 16 for RK4 and is 4.00 for Verlet.
10. In that script set `ECCENTRICITY = 0.9`. Prediction: both errors grow a lot, because at periapsis
    (r = 10) the particle moves fast and the force changes quickly, so a fixed step is too coarse there.
    This is the motivation for adaptive step sizes in 1C-2.
11. Set `SEMI_MAJOR_AXIS = 1000` with the same steps per orbit. Prediction: the end error grows exactly
    tenfold, so the error relative to a stays the same. With GM = 1 the problem has no length scale of
    its own: the same number of steps per orbit gives the same relative accuracy at every size.
12. In a Python prompt, integrate the circular orbit with Euler's method yourself:

    ```python
    import numpy as np
    from bhlab.physics.newtonian import acceleration, circular_orbit, specific_energy

    y = circular_orbit(100.0)
    h = 6.283
    for _ in range(1000):
        y = y + h * np.concatenate((y[2:], acceleration(y[:2])))
    print(np.hypot(y[0], y[1]), specific_energy(y))
    ```

    Prediction: after one orbit the radius has grown to about 107.7 and the energy has risen from
    −0.005 to −0.00466. Euler spirals outward. RK4 with the same step stays at 100 to within 10⁻⁷.

13. Run `.venv\Scripts\python.exe -m bhlab.orbit --orbits 3`. Prediction: apoapsis at 3142, 9425 and
    15708 GM/c³, that is (k + ½)·T. Then add `--mass 4.3e6` and check that the period reads 1.540 d.
14. Fall from rest: `--x 10 --vy 0 --stop-radius 2`. Prediction: it stops at t = 33.70 GM/c³ (section
    2.13). Repeat with `--stop-radius 1` and work out the new time by hand first.
15. Escape: `--vy 0.25 --duration 2000`. Prediction: "unbound", e = 2.125, period ∞. Without
    `--duration` the program refuses to run; read its message and explain why.
16. Loosen the tolerance: `--orbits 3 --rtol 1e-5`. Prediction: far fewer steps and a larger energy
    error. The event times change only slightly; compare them with (k + ½)·T.
17. In `examples\integrator_comparison.py` set `ECCENTRICITY = 0.9` and compare the "evaluations" of
    DOP853 with the 4 per step of RK4 at a similar end error.

## 7. To study next

Before Checkpoint 1D (placing particles and running them in the window):

- Qt timers and the animation loop: redrawing the screen at a steady rate while time passes.
- Why the physics time step must not depend on the frame rate, and how to step a simulation by a
  fixed amount of simulated time per frame.
- Mouse events in pyqtgraph: turning a click and drag into a position and a velocity.

Further ahead, for Stage 2: the idea of a metric, proper time against coordinate time, and the
effective potential of an orbit.

Textbook references will be added here once they have been checked.

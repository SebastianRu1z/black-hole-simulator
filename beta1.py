"""
black_hole_orbits.py -- interactive gravity sandbox around a Schwarzschild
black hole.  Drop planets at any radius and watch what general relativity
does to them.

    python black_hole_orbits.py                  (interactive window)
    python black_hole_orbits.py --mass 4.3e6     (Sagittarius A*-sized hole)
    python black_hole_orbits.py --selftest       (check the physics, no window)

CONTROLS
    click in the map ....... drop a planet at that spot
    Radius slider + Add .... drop a planet at an exact radius (units of M)
    Speed slider ........... launch speed as a multiple of the circular-orbit
                             speed at that radius (1.0 = circular orbit)
    Time rate slider ....... far-away-observer time per animation frame
    Newton ghosts button ... dashed path = what Newtonian gravity predicts
                             for the same launch, for comparison

THE MATH  (units G = c = M = 1; view is the orbital plane seen from above)

Each planet is a test particle following a timelike geodesic of

    ds^2 = -(1 - 2/r) dt^2 + dr^2/(1 - 2/r) + r^2 dphi^2

which conserves energy E = (1 - 2/r) dt/dtau and angular momentum
L = r^2 dphi/dtau (both per unit rest mass).  The equations of motion are

    d^2r/dtau^2 = -1/r^2 + L^2/r^3 - 3 L^2/r^4
    dphi/dtau   = L / r^2
    dt/dtau     = E / (1 - 2/r)

The first two terms of the radial equation are Newton (gravity and the
centrifugal barrier).  The last term, -3L^2/r^4, is pure general relativity:
it makes orbits precess, makes circular orbits unstable inside r = 6M, and
means that close in, MORE angular momentum pulls you in harder.

The simulation is advanced in t, the time of a far-away observer, so you
see what a distant astronomer would: infalling objects slow down and freeze
at the horizon.  Each planet also carries its own clock (proper time tau)
so you can read off the time dilation.

A launch at radius r with tangential speed v (as measured by an observer
hovering at r) has  E = sqrt(1 - 2/r) * gamma,  L = r * gamma * v,
gamma = 1/sqrt(1 - v^2).  The circular-orbit speed is v_c = sqrt(1/(r - 2)).

Planets are test particles: they feel the hole but not each other, and they
do not radiate gravitational waves.
"""
import argparse
import math
import sys
from collections import deque

import numpy as np

import bh_physics as bh

R_CAPTURE = 2.02        # treat as swallowed once this close to the horizon
R_ESCAPE = 600.0
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))
COLOURS = ["#4fc3f7", "#ffb74d", "#aed581", "#f06292", "#ba68c8",
           "#fff176", "#4dd0e1", "#ff8a65", "#90a4ae", "#e6ee9c"]


def geodesic_rhs(r, pr, L, E):
    """d/dt of (r, phi, pr, tau) with t = far-observer time."""
    f = max(1.0 - 2.0 / r, 1e-9)
    dtau_dt = f / E
    L2 = L * L
    return (pr * dtau_dt,
            L / (r * r) * dtau_dt,
            (-1.0 / r**2 + L2 / r**3 - 3.0 * L2 / r**4) * dtau_dt,
            dtau_dt)


class Planet:
    """A test mass on a Schwarzschild geodesic, plus a Newtonian twin."""

    def __init__(self, r0, phi0, speed_factor, colour="w", name=""):
        self.name, self.colour = name, colour
        self.r0, self.k = r0, speed_factor
        f = 1.0 - 2.0 / r0
        v = min(speed_factor * bh.circular_speed(r0), 0.9999)   # < c
        gamma = 1.0 / math.sqrt(1.0 - v * v)
        self.E = math.sqrt(f) * gamma
        self.L = r0 * gamma * v
        self.r, self.phi, self.pr, self.tau = r0, phi0, 0.0, 0.0
        self.status = "orbiting"
        self.trail = deque(maxlen=2500)

        # Newtonian twin: same radius, same multiple of ITS circular speed
        vn = speed_factor * math.sqrt(1.0 / r0)
        self.nx, self.ny = r0 * math.cos(phi0), r0 * math.sin(phi0)
        self.nvx, self.nvy = -vn * math.sin(phi0), vn * math.cos(phi0)
        self.n_alive = True
        self.n_trail = deque(maxlen=2500)

    # --- relativistic motion ------------------------------------------------
    def advance(self, dt):
        left = dt
        while left > 1e-12 and self.status == "orbiting":
            # step is a small fraction of the local orbital timescale
            h = min(left, 0.02 * self.r**1.5)
            r, phi, pr, tau, L, E = self.r, self.phi, self.pr, self.tau, self.L, self.E
            a1 = geodesic_rhs(r, pr, L, E)
            a2 = geodesic_rhs(r + 0.5 * h * a1[0], pr + 0.5 * h * a1[2], L, E)
            a3 = geodesic_rhs(r + 0.5 * h * a2[0], pr + 0.5 * h * a2[2], L, E)
            a4 = geodesic_rhs(r + h * a3[0], pr + h * a3[2], L, E)
            self.r = r + h / 6 * (a1[0] + 2 * a2[0] + 2 * a3[0] + a4[0])
            self.phi = phi + h / 6 * (a1[1] + 2 * a2[1] + 2 * a3[1] + a4[1])
            self.pr = pr + h / 6 * (a1[2] + 2 * a2[2] + 2 * a3[2] + a4[2])
            self.tau = tau + h / 6 * (a1[3] + 2 * a2[3] + 2 * a3[3] + a4[3])
            left -= h
            if self.r < R_CAPTURE:
                self.status = "captured"
            elif self.r > R_ESCAPE:
                self.status = "escaped"

    # --- Newtonian twin (velocity-Verlet) -----------------------------------
    def advance_newton(self, dt):
        left = dt
        while left > 1e-12 and self.n_alive:
            r = math.hypot(self.nx, self.ny)
            if r < 2.0 or r > R_ESCAPE:
                self.n_alive = False
                break
            h = min(left, 0.02 * r**1.5)
            ax, ay = -self.nx / r**3, -self.ny / r**3
            self.nvx += 0.5 * h * ax
            self.nvy += 0.5 * h * ay
            self.nx += h * self.nvx
            self.ny += h * self.nvy
            r = math.hypot(self.nx, self.ny)
            self.nvx -= 0.5 * h * self.nx / r**3
            self.nvy -= 0.5 * h * self.ny / r**3
            left -= h

    # --- diagnostics ---------------------------------------------------------
    @property
    def xy(self):
        return self.r * math.cos(self.phi), self.r * math.sin(self.phi)

    @property
    def local_speed(self):
        """Speed measured by a static observer at the planet's position."""
        f = 1.0 - 2.0 / self.r
        return math.sqrt(max(0.0, 1.0 - f / self.E**2))

    @property
    def energy_error(self):
        """|E recomputed from the current state - E conserved|: integrator check."""
        e2 = self.pr**2 + bh.effective_potential_sq(self.r, self.L)
        return abs(math.sqrt(max(e2, 0.0)) - self.E)

    def fate(self):
        """Predict the outcome from E and L alone (no integration needed)."""
        if self.L * self.L <= 12.0:
            return "no barrier: falls in"
        # peak of V^2 is at the unstable circular radius
        r_peak = self.L**2 / 2 * (1 - math.sqrt(1 - 12 / self.L**2))
        v_peak = bh.effective_potential_sq(r_peak, self.L)
        if self.r0 < r_peak or self.E**2 > v_peak:
            return "falls in"
        return "escapes" if self.E >= 1.0 else "bound orbit"


# ---------------------------------------------------------------------------
# Self-test: compare the integrator against known analytic results
# ---------------------------------------------------------------------------
def selftest():
    ok = True

    def check(label, passed, detail):
        nonlocal ok
        ok &= passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}: {detail}")

    print("Schwarzschild geodesic self-test")

    p = Planet(10.0, 0.0, 1.0)
    drift = 0.0
    for _ in range(2000):
        p.advance(5.0)
        drift = max(drift, abs(p.r - 10.0))
    check("circular orbit at 10M stays circular", drift < 1e-6, f"max |dr| = {drift:.2e} M")

    # far-observer period of a circular orbit is exactly 2 pi r^1.5
    p = Planet(8.0, 0.0, 1.0)
    t, dt = 0.0, 0.01
    while p.phi < 2 * math.pi:
        p.advance(dt)
        t += dt
    exact = 2 * math.pi * 8.0**1.5
    check("orbital period at 8M", abs(t - exact) / exact < 1e-3,
          f"{t:.2f} M vs exact {exact:.2f} M")

    # perihelion precession in the weak field: 6 pi M / (a (1 - e^2)) per orbit
    p = Planet(200.0, 0.0, 1.1)
    peri_phi, prev_pr, rmax = [], 0.0, 200.0
    for _ in range(400000):
        p.advance(1.0)
        rmax = max(rmax, p.r)
        if prev_pr < 0 <= p.pr:
            peri_phi.append(p.phi)
            if len(peri_phi) == 3:
                break
        prev_pr = p.pr
    measured = peri_phi[2] - peri_phi[1] - 2 * math.pi
    a, e = (rmax + 200.0) / 2, (rmax - 200.0) / (rmax + 200.0)
    predicted = 6 * math.pi / (a * (1 - e * e))
    check("perihelion precession (a = %.0f M, e = %.2f)" % (a, e),
          abs(measured - predicted) / predicted < 0.05,
          f"{math.degrees(measured):.3f} deg/orbit vs first-order formula {math.degrees(predicted):.3f}")

    p = Planet(7.0, 0.0, 0.995)
    for _ in range(4000):
        p.advance(5.0)
    check("slightly slow launch at 7M (outside ISCO) survives", p.status == "orbiting",
          f"status = {p.status}, r = {p.r:.2f} M")

    p = Planet(5.0, 0.0, 0.995)
    for _ in range(4000):
        p.advance(5.0)
    check("same launch at 5M (inside ISCO) is swallowed", p.status == "captured",
          f"status = {p.status}")

    p = Planet(12.0, 0.0, 0.8)
    err = 0.0
    for _ in range(4000):
        p.advance(5.0)
        err = max(err, p.energy_error)
    check("energy conservation on an eccentric orbit", err < 1e-6, f"max |dE| = {err:.2e}")

    print("All checks passed." if ok else "SOME CHECKS FAILED.")
    return ok


# ---------------------------------------------------------------------------
# Interactive application
# ---------------------------------------------------------------------------
class Sandbox:
    VIEW = 45.0     # half-width of the map in M

    def __init__(self, mass_solar):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, Slider
        self.plt = plt
        self.hole = bh.BlackHole(mass_solar)
        self.planets, self.artists = [], {}
        self.t, self.count, self.swallowed = 0.0, 0, 0
        self.paused, self.show_newton = False, True

        plt.style.use("dark_background")
        self.fig = fig = plt.figure(figsize=(14.5, 8.6))
        fig.canvas.manager.set_window_title("Black hole gravity sandbox")

        # --- map ------------------------------------------------------------
        self.ax = ax = fig.add_axes([0.035, 0.235, 0.50, 0.735])
        V = self.VIEW
        n = 500
        xs = np.linspace(-V, V, n)
        X, Y = np.meshgrid(xs, xs)
        R = np.hypot(X, Y)
        with np.errstate(invalid="ignore", divide="ignore"):
            g = np.where(R > 2.0, bh.static_gravity(np.maximum(R, 2.0001)), np.nan)
        im = ax.imshow(np.log10(g), extent=[-V, V, -V, V], origin="lower",
                       cmap="inferno", vmin=-3.4, vmax=-0.5, alpha=0.85)
        cax = fig.add_axes([0.085, 0.165, 0.40, 0.011])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal")
        cb.set_label(r"log$_{10}$ of the acceleration needed to hover,  "
                     r"$g = M / (r^2\sqrt{1-2M/r})$   [units of $c^4/GM$]", fontsize=8)
        cb.ax.tick_params(labelsize=7)

        th = np.linspace(0, 2 * np.pi, 400)
        ax.fill(2 * np.cos(th), 2 * np.sin(th), color="black", zorder=5)
        ax.plot(2 * np.cos(th), 2 * np.sin(th), color="white", lw=0.8, zorder=6)
        for radius, style, label in [(3.0, ":", "photon sphere 3M"),
                                     (6.0, "--", "ISCO 6M")]:
            ax.plot(radius * np.cos(th), radius * np.sin(th), ls=style, lw=0.9,
                    color="#cccccc", zorder=4, label=label)
        ax.plot([], [], color="white", lw=0.8, label="event horizon 2M")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.4)
        ax.set_xlim(-V, V)
        ax.set_ylim(-V, V)
        ax.set_aspect("equal")
        ax.set_xlabel("x  [M = GM/c²]")
        ax.set_ylabel("y  [M]")
        ax.set_title("Orbital plane from above — click to drop a planet", fontsize=11)

        # --- effective potential ---------------------------------------------
        self.ax_v = axv = fig.add_axes([0.60, 0.60, 0.375, 0.34])
        axv.set_title("Effective potential of the newest planet", fontsize=10)
        axv.set_xlabel("r  [M]")
        axv.set_ylabel(r"$V^2 = (1-2/r)(1+L^2/r^2)$")
        axv.set_xlim(2, V)
        axv.axvline(6, color="#888", ls="--", lw=0.7)
        axv.axvline(3, color="#888", ls=":", lw=0.7)
        self.v_r = np.linspace(2.0, V, 600)
        (self.v_curve,) = axv.plot([], [], color="#4fc3f7", lw=1.5, label="V²(r)")
        (self.v_newton,) = axv.plot([], [], color="#888", lw=1.0, ls="-.",
                                    label="without the GR term")
        self.v_energy = axv.axhline(1.0, color="#ffb74d", lw=1.0, label="E² (its energy)")
        (self.v_dot,) = axv.plot([], [], "o", color="white", ms=6)
        axv.legend(fontsize=7, loc="lower right", framealpha=0.4)

        # --- readout -----------------------------------------------------------
        self.ax_info = axi = fig.add_axes([0.60, 0.20, 0.375, 0.33])
        axi.axis("off")
        self.info = axi.text(0, 1, "", va="top", ha="left", family="monospace", fontsize=8)

        # --- widgets -----------------------------------------------------------
        dark = "#222831"
        self.s_radius = Slider(fig.add_axes([0.13, 0.085, 0.27, 0.022]), "Radius [M]",
                               2.2, 40.0, valinit=10.0, color="#4fc3f7")
        self.s_speed = Slider(fig.add_axes([0.13, 0.050, 0.27, 0.022]), "Speed × circular",
                              0.0, 1.5, valinit=1.0, color="#ffb74d")
        self.s_rate = Slider(fig.add_axes([0.13, 0.015, 0.27, 0.022]), "Time rate [M/frame]",
                             0.1, 25.0, valinit=3.0, color="#aed581")
        self.b_add = Button(fig.add_axes([0.46, 0.075, 0.075, 0.04]), "Add planet",
                            color=dark, hovercolor="#3a4750")
        self.b_pause = Button(fig.add_axes([0.46, 0.022, 0.075, 0.04]), "Pause",
                              color=dark, hovercolor="#3a4750")
        self.b_clear = Button(fig.add_axes([0.55, 0.075, 0.075, 0.04]), "Clear all",
                              color=dark, hovercolor="#3a4750")
        self.b_demo = Button(fig.add_axes([0.55, 0.022, 0.075, 0.04]), "Demo set",
                             color=dark, hovercolor="#3a4750")
        self.b_newton = Button(fig.add_axes([0.64, 0.075, 0.11, 0.04]), "Newton ghosts: on",
                               color=dark, hovercolor="#3a4750")
        self.hint = fig.text(0.80, 0.03, "", fontsize=8, color="#cccccc", va="bottom")

        self.b_add.on_clicked(lambda _e: self.add(self.s_radius.val))
        self.b_pause.on_clicked(self.toggle_pause)
        self.b_clear.on_clicked(lambda _e: self.clear())
        self.b_demo.on_clicked(lambda _e: self.demo())
        self.b_newton.on_clicked(self.toggle_newton)
        self.s_radius.on_changed(lambda _v: self.update_hint())
        self.s_speed.on_changed(lambda _v: self.update_hint())
        fig.canvas.mpl_connect("button_press_event", self.on_click)

        self.update_hint()
        self.demo()

    # --- actions -----------------------------------------------------------
    def update_hint(self):
        r, k = self.s_radius.val, self.s_speed.val
        if r <= 3.0:
            zone = "inside photon sphere:\nno orbit possible below light speed"
        elif r < 6.0:
            zone = "inside ISCO:\ncircular orbit exists but is unstable"
        else:
            zone = "outside ISCO:\nstable orbits possible"
        v = min(k * bh.circular_speed(r), 0.9999)
        self.hint.set_text(f"r = {r:.1f} M  →  {zone}\nlaunch speed = {v:.3f} c")

    def add(self, r, phi=None, k=None):
        if r <= 2.1:
            return
        if phi is None:
            phi = self.count * GOLDEN_ANGLE
        k = self.s_speed.val if k is None else k
        self.count += 1
        p = Planet(r, phi, k, COLOURS[(self.count - 1) % len(COLOURS)], f"P{self.count}")
        self.planets.append(p)
        (trail,) = self.ax.plot([], [], color=p.colour, lw=1.1, alpha=0.9, zorder=7)
        (ghost,) = self.ax.plot([], [], color=p.colour, lw=0.8, ls="--", alpha=0.55, zorder=6)
        (dot,) = self.ax.plot([], [], "o", color=p.colour, ms=7, mec="white", mew=0.6, zorder=9)
        (gdot,) = self.ax.plot([], [], "o", color=p.colour, ms=4, alpha=0.55, zorder=8)
        label = self.ax.text(0, 0, p.name, color=p.colour, fontsize=7, zorder=10)
        self.artists[p] = (trail, ghost, dot, gdot, label)
        self.show_potential(p)

    def remove(self, p):
        for artist in self.artists.pop(p):
            artist.remove()
        self.planets.remove(p)

    def clear(self):
        for p in list(self.planets):
            self.remove(p)
        self.t, self.count, self.swallowed = 0.0, 0, 0

    def demo(self):
        self.clear()
        self.add(8.0, 0.0, 1.0)      # stable circular orbit just outside the ISCO
        self.add(24.0, 2.0, 0.85)    # eccentric: strong relativistic precession
        self.add(32.0, 4.0, 1.0)     # distant, nearly Newtonian circle
        self.add(5.0, 1.0, 0.99)     # inside the ISCO: spirals in
        self.add(14.0, 5.2, 0.45)    # too slow: plunges; Newton says it survives

    def toggle_pause(self, _event):
        self.paused = not self.paused
        self.b_pause.label.set_text("Resume" if self.paused else "Pause")

    def toggle_newton(self, _label):
        self.show_newton = not self.show_newton
        self.b_newton.label.set_text(f"Newton ghosts: {'on' if self.show_newton else 'off'}")

    def on_click(self, event):
        if event.inaxes is not self.ax or event.button != 1:
            return
        if self.fig.canvas.toolbar is not None and self.fig.canvas.toolbar.mode:
            return                                   # zoom/pan tool is active
        r = math.hypot(event.xdata, event.ydata)
        self.add(r, math.atan2(event.ydata, event.xdata))

    def show_potential(self, p):
        r = self.v_r
        v2 = bh.effective_potential_sq(r, p.L)
        self.v_curve.set_data(r, v2)
        # Newtonian-like potential: drop the -2L^2/r^3 cross term that GR adds
        self.v_newton.set_data(r, 1 - 2 / r + p.L**2 / r**2)
        self.v_energy.set_ydata([p.E**2, p.E**2])
        lo = min(v2[r > 2.5].min(), p.E**2)
        hi = max(min(v2.max(), 1.6), p.E**2, 1.02)
        pad = 0.08 * (hi - lo)
        self.ax_v.set_ylim(lo - pad, hi + pad)
        self.ax_v.set_title(f"Effective potential of {p.name}  (L = {p.L:.2f}, E = {p.E:.4f})",
                            fontsize=10)
        self.v_planet = p

    # --- animation ---------------------------------------------------------
    def step(self, _frame=None):
        if not self.paused:
            dt = self.s_rate.val
            self.t += dt
            for p in list(self.planets):
                p.advance(dt)
                p.advance_newton(dt)
                if p.status == "orbiting":
                    p.trail.append(p.xy)
                if p.n_alive:
                    p.n_trail.append((p.nx, p.ny))
                if p.status == "escaped":
                    self.remove(p)
                elif p.status == "captured" and not getattr(p, "counted", False):
                    p.counted = True
                    self.swallowed += 1
        self.draw()
        return []

    def draw(self):
        for p, (trail, ghost, dot, gdot, label) in self.artists.items():
            if p.trail:
                tx, ty = zip(*p.trail)
                trail.set_data(tx, ty)
            x, y = p.xy
            dot.set_data([x], [y])
            dot.set_alpha(0.35 if p.status == "captured" else 1.0)
            label.set_position((x + 1.0, y + 1.0))
            visible = self.show_newton
            ghost.set_visible(visible)
            gdot.set_visible(visible and p.n_alive)
            if visible and p.n_trail:
                gx, gy = zip(*p.n_trail)
                ghost.set_data(gx, gy)
                gdot.set_data([p.nx], [p.ny])

        p = getattr(self, "v_planet", None)
        if p is not None and p in self.artists:
            self.v_dot.set_data([p.r], [bh.effective_potential_sq(p.r, p.L)])
        else:
            self.v_dot.set_data([], [])

        hole = self.hole
        lines = [
            f"Black hole: {hole.mass_solar:g} solar masses   "
            f"(1 M = {hole.length_m / 1000:.4g} km = {hole.time_s:.3g} s)",
            f"Far-observer time: {self.t:9.1f} M = {self.t * hole.time_s:.4g} s"
            f"     swallowed: {self.swallowed}",
            "",
            "name   r[M]   speed   own clock   clock    status",
            "             [c]     tau [M]     rate",
        ]
        for p in self.planets[-12:]:
            if p.status == "captured":
                lines.append(f"{p.name:<5}{p.r:6.2f}    --   {p.tau:9.1f}   frozen   at horizon")
            else:
                rate = (1 - 2 / p.r) / p.E          # d tau / dt
                lines.append(f"{p.name:<5}{p.r:6.2f}  {p.local_speed:5.3f}  {p.tau:9.1f}"
                             f"   {rate:5.3f}    {p.fate()}")
        lines += ["",
                  "clock rate = planet seconds per far-observer second",
                  "solid = general relativity    dashed = Newton"]
        self.info.set_text("\n".join(lines))

    def run(self):
        from matplotlib.animation import FuncAnimation
        self.anim = FuncAnimation(self.fig, self.step, interval=30,
                                  cache_frame_data=False)
        self.plt.show()


def main():
    ap = argparse.ArgumentParser(description="Interactive Schwarzschild orbit sandbox.")
    ap.add_argument("--mass", type=float, default=10.0, help="black hole mass in solar masses")
    ap.add_argument("--selftest", action="store_true", help="verify the physics and exit")
    ap.add_argument("--snapshot", metavar="PNG",
                    help="run 400 frames without a window and save a picture")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    print(bh.BlackHole(args.mass).summary())
    if args.snapshot:
        import matplotlib
        matplotlib.use("Agg")
        app = Sandbox(args.mass)
        for _ in range(400):
            app.step()
        app.fig.savefig(args.snapshot, dpi=90)
        print(f"Saved {args.snapshot}")
    else:
        Sandbox(args.mass).run()


if __name__ == "__main__":
    main()

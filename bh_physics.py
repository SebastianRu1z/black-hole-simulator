"""
bh_physics.py -- the physics shared by the renderer and the orbit simulator.

Everything here is for a SCHWARZSCHILD black hole: non-rotating, uncharged,
described exactly by general relativity with the metric

    ds^2 = -(1 - 2M/r) dt^2 + dr^2 / (1 - 2M/r) + r^2 (dtheta^2 + sin^2(theta) dphi^2)

The simulations work in "geometric units" where G = c = 1 and the black hole
mass M = 1.  In those units every length is a multiple of GM/c^2 and every
time is a multiple of GM/c^3.  The BlackHole class converts back to SI.

Key radii (all exact results of the metric above):
    event horizon         r = 2M    (Schwarzschild radius r_s = 2GM/c^2)
    photon sphere         r = 3M    (light can orbit; unstable)
    marginally bound      r = 4M    (a parabolic infall with less angular
                                     momentum than this is captured)
    ISCO                  r = 6M    (innermost stable circular orbit)
    critical impact par.  b = sqrt(27) M  (edge of the black hole "shadow")
"""
import math

import numpy as np

# --- SI constants ---------------------------------------------------------
G = 6.67430e-11          # m^3 kg^-1 s^-2
C = 2.99792458e8         # m / s
HBAR = 1.054571817e-34   # J s
K_B = 1.380649e-23       # J / K
M_SUN = 1.98847e30       # kg

# --- Key radii in units of M (G = c = 1) ----------------------------------
R_HORIZON = 2.0
R_PHOTON = 3.0
R_MARGINALLY_BOUND = 4.0
R_ISCO = 6.0
B_CRIT = math.sqrt(27.0)


class BlackHole:
    """Converts between geometric units (M = 1) and SI for a given mass."""

    def __init__(self, mass_solar=10.0):
        self.mass_solar = mass_solar
        self.mass_kg = mass_solar * M_SUN
        self.length_m = G * self.mass_kg / C**2      # 1 M of length, in metres
        self.time_s = G * self.mass_kg / C**3        # 1 M of time, in seconds

    @property
    def schwarzschild_radius_m(self):
        return 2.0 * self.length_m

    @property
    def hawking_temperature_K(self):
        # T_H = hbar c^3 / (8 pi G M k_B)
        return HBAR * C**3 / (8 * math.pi * G * self.mass_kg * K_B)

    def tidal_acceleration(self, r_M, body_length_m=2.0):
        """Radial stretching (m/s^2) across a body of given length at radius r.
        For radial free fall the tidal tensor gives  2GM L / r^3  exactly."""
        r = r_M * self.length_m
        return 2 * G * self.mass_kg * body_length_m / r**3

    def summary(self):
        km = self.length_m / 1000.0
        isco_period = 2 * math.pi * R_ISCO**1.5 * self.time_s
        lines = [
            f"Schwarzschild black hole, mass = {self.mass_solar:g} solar masses",
            f"  1 M of length (GM/c^2)        = {km:.4g} km",
            f"  1 M of time   (GM/c^3)        = {self.time_s:.4g} s",
            f"  event horizon     r = 2M      = {2 * km:.4g} km",
            f"  photon sphere     r = 3M      = {3 * km:.4g} km",
            f"  ISCO              r = 6M      = {6 * km:.4g} km",
            f"  shadow radius     b = 5.196M  = {B_CRIT * km:.4g} km",
            f"  ISCO orbital speed (local)    = {circular_speed(6.0):.3f} c",
            f"  ISCO orbital period (far obs) = {isco_period:.4g} s",
            f"  ISCO binding energy           = {(1 - circular_energy(6.0)) * 100:.2f} % of rest mass",
            f"  Hawking temperature           = {self.hawking_temperature_K:.3g} K",
            f"  tidal stretch on 2 m at 2M    = {self.tidal_acceleration(2.0):.3g} m/s^2",
        ]
        return "\n".join(lines)


# --- Orbits of massive particles (timelike geodesics), M = 1 --------------
#
# In the equatorial plane a geodesic conserves
#     E = (1 - 2/r) dt/dtau      energy per unit rest mass
#     L = r^2 dphi/dtau          angular momentum per unit rest mass
# and the radial motion obeys
#     (dr/dtau)^2 = E^2 - V(r)^2,   V^2 = (1 - 2/r)(1 + L^2/r^2)

def lapse(r):
    """sqrt(1 - 2M/r): rate of a static clock at r relative to one far away."""
    return np.sqrt(1.0 - 2.0 / r)


def circular_speed(r):
    """Speed of a circular orbit as measured by a static observer at r.
    v = sqrt(M / (r - 2M)).  Reaches c at the photon sphere r = 3M."""
    return math.sqrt(1.0 / (r - 2.0))


def circular_energy(r):
    """E of a circular orbit: (1 - 2/r) / sqrt(1 - 3/r)."""
    return (1.0 - 2.0 / r) / math.sqrt(1.0 - 3.0 / r)


def circular_angular_momentum(r):
    """L of a circular orbit: sqrt(r) / sqrt(1 - 3/r)."""
    return math.sqrt(r) / math.sqrt(1.0 - 3.0 / r)


def effective_potential_sq(r, L):
    """V^2(r) = (1 - 2/r)(1 + L^2/r^2)."""
    return (1.0 - 2.0 / r) * (1.0 + L * L / (r * r))


def static_gravity(r):
    """Proper acceleration needed to hover at radius r (units of c^4/GM):
        g = M / (r^2 sqrt(1 - 2M/r))
    Newton's M/r^2 with a relativistic factor that diverges at the horizon."""
    return 1.0 / (r * r * np.sqrt(1.0 - 2.0 / r))


# --- Accretion disc: Page & Thorne (1974) flux for a = 0 ------------------

def page_thorne_flux(r):
    """Energy flux radiated from each face of a thin relativistic accretion
    disc around a Schwarzschild hole (Page & Thorne 1974, spin a = 0).
    With x = sqrt(r/M):

        F(x) ~ 1 / (x^5 (x^2 - 3)) *
               [ x - sqrt6 + (sqrt3/2) ln( (x+sqrt3)(sqrt6-sqrt3) /
                                           ((x-sqrt3)(sqrt6+sqrt3)) ) ]

    Zero at the ISCO (r = 6M), peaks near r = 9.55M, falls as r^-3 far away.
    Returned in arbitrary units (the 3 Mdot / 8 pi M^2 prefactor is dropped).
    """
    r = np.asarray(r, dtype=float)
    x = np.sqrt(np.maximum(r, R_ISCO))
    s3, s6 = math.sqrt(3.0), math.sqrt(6.0)
    bracket = x - s6 + (s3 / 2.0) * np.log(
        (x + s3) * (s6 - s3) / ((x - s3) * (s6 + s3)))
    return np.maximum(bracket, 0.0) / (x**5 * (x * x - 3.0))


# --- Black-body colour -----------------------------------------------------

_RGB_WAVELENGTHS = np.array([610e-9, 550e-9, 465e-9])   # m
_HC_OVER_K = 1.438776877e-2                             # m K


def planck_rgb(T, T_ref=6500.0):
    """Planck spectral radiance B_lambda(T) sampled at red, green and blue
    wavelengths, normalised so that green at T_ref equals 1.
    T may be an array; the result has a trailing axis of size 3."""
    T = np.asarray(T, dtype=float)[..., None]
    lam = _RGB_WAVELENGTHS
    with np.errstate(over="ignore", divide="ignore"):
        b = lam**-5 / np.expm1(_HC_OVER_K / (lam * np.maximum(T, 1.0)))
    ref = lam[1]**-5 / math.expm1(_HC_OVER_K / (lam[1] * T_ref))
    return b / ref

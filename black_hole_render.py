"""
black_hole_render.py -- ray-traced image of a Schwarzschild black hole with
an accretion disc, as seen by a nearby observer.

    python black_hole_render.py                     (default view)
    python black_hole_render.py --incl 60 --width 1600 --height 900
    python black_hole_render.py --help

HOW IT WORKS  (units G = c = M = 1)

1. Light paths.  One ray per pixel is traced BACKWARDS from the camera.
   A photon in the Schwarzschild metric moves in a plane and obeys

        d^2u/dphi^2 + u = 3 M u^2 ,     u = 1/r

   This is exactly the orbit of a particle in flat space feeling the force

        d^2x/dlambda^2 = -3 M h^2 x / r^5 ,   h = |x cross dx/dlambda|

   (h is conserved, so the two equations describe the same curve.)  That
   lets us integrate in Cartesian coordinates with RK4 and get the exact
   bending of light, including the photon sphere at r = 3M and the shadow
   of radius sqrt(27) M.

2. The disc.  A thin disc of gas on circular orbits in the plane z = 0,
   from the ISCO (r = 6M) outwards.  Its surface brightness follows the
   Page-Thorne relativistic thin-disc flux F(r); temperature T ~ F^(1/4).

3. What the camera sees.  Gas at radius r orbits with angular velocity
   Omega = sqrt(M/r^3).  The frequency shift of a photon from it is

        g = nu_obs / nu_emit
          = sqrt(1 - 3M/r) / (1 - Omega * l)  /  sqrt(1 - 2M/r_cam)

   where l = L_z/E is the photon's angular momentum about the disc axis.
   This single factor contains BOTH the Doppler shift and the gravitational
   redshift.  Because I_nu / nu^3 is invariant along a ray, a black body of
   temperature T is seen as a black body of temperature g*T -- so the side
   rotating toward us is hotter, bluer and far brighter (relativistic
   beaming) while the receding side is dim and red.

4. Rays that reach r = 2M are black; rays that escape sample a star field.

Not physical, added only so the image reads well: faint streaks in the disc
(a real disc is turbulent, a smooth one looks like plastic), the star field
is random, and a soft glow (bloom) imitates a camera lens.  The disc
temperature is scaled to a few thousand K so the colours fall in visible
light; a real disc around a stellar-mass hole peaks in X-rays.
"""
import argparse
import math
import time

import numpy as np

import bh_physics as bh


def make_star_map(height=1024, n_stars=9000, seed=7):
    """Random star field on an equirectangular (theta, phi) map."""
    rng = np.random.default_rng(seed)
    tex = np.zeros((height, 2 * height, 3))
    # uniform on the sphere: cos(theta) uniform in [-1, 1]
    theta = np.arccos(rng.uniform(-1, 1, n_stars))
    phi = rng.uniform(0, 2 * np.pi, n_stars)
    iy = np.minimum((theta / np.pi * height).astype(int), height - 1)
    ix = np.minimum((phi / (2 * np.pi) * 2 * height).astype(int), 2 * height - 1)
    temps = rng.uniform(3000, 12000, n_stars)
    colour = bh.planck_rgb(temps)
    colour /= colour.max(axis=1, keepdims=True)
    brightness = 0.3 * rng.pareto(2.0, n_stars) + 0.05
    tex[iy, ix] = colour * np.minimum(brightness, 6.0)[:, None]
    return tex


def sample_star_map(tex, direction):
    h = tex.shape[0]
    d = direction / np.linalg.norm(direction, axis=1, keepdims=True)
    theta = np.arccos(np.clip(d[:, 2], -1, 1))
    phi = np.mod(np.arctan2(d[:, 1], d[:, 0]), 2 * np.pi)
    iy = np.minimum((theta / np.pi * h).astype(int), h - 1)
    ix = np.minimum((phi / (2 * np.pi) * 2 * h).astype(int), 2 * h - 1)
    return tex[iy, ix]


def shade_disc(hit, lz_over_E, r_cam, T_peak, flux_max, texture):
    """Observed RGB radiance of the disc at the points `hit` (N, 3)."""
    r = np.hypot(hit[:, 0], hit[:, 1])
    phi = np.arctan2(hit[:, 1], hit[:, 0])

    T_emit = T_peak * (bh.page_thorne_flux(r) / flux_max) ** 0.25
    omega = r ** -1.5                                   # Keplerian, exact in GR
    g = np.sqrt(1.0 - 3.0 / r) / (1.0 - omega * lz_over_E)
    g /= math.sqrt(1.0 - 2.0 / r_cam)                   # static camera at r_cam

    rgb = bh.planck_rgb(g * T_emit, T_ref=T_peak)       # black body at g*T
    if texture:
        streaks = (0.80
                   + 0.12 * np.sin(5 * phi + 14 * np.log(r))
                   + 0.08 * np.sin(13 * phi - 23 * np.log(r) + 1.3))
        rgb *= streaks[:, None]
    return rgb


def trace(width, height, r_cam=70.0, incl_deg=80.0, fov_deg=40.0,
          r_out=20.0, T_peak=3800.0, texture=True, verbose=True):
    """Trace width*height rays; returns a linear-light image (H, W, 3)."""
    r_in = bh.R_ISCO
    r_escape = 2.0 * max(r_cam, r_out)

    # --- camera -----------------------------------------------------------
    inc = math.radians(incl_deg)            # angle from the disc's spin axis
    cam = r_cam * np.array([math.sin(inc), 0.0, math.cos(inc)])
    forward = -cam / r_cam
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    half = math.tan(math.radians(fov_deg) / 2)
    xs = np.linspace(-half, half, width)
    ys = np.linspace(half, -half, height) * (height / width)
    px, py = np.meshgrid(xs, ys)
    d = (forward[None, :] + px.reshape(-1, 1) * right[None, :]
         + py.reshape(-1, 1) * up[None, :])
    d /= np.linalg.norm(d, axis=1, keepdims=True)

    # A static observer at r_cam measures radial distance stretched by
    # 1/sqrt(1-2M/r).  Convert the locally measured direction into a
    # Schwarzschild-coordinate direction: tangential part grows by 1/sqrt(f).
    rhat = cam / r_cam
    d_rad = (d @ rhat)[:, None] * rhat[None, :]
    d = d_rad + (d - d_rad) / math.sqrt(1.0 - 2.0 / r_cam)
    d /= np.linalg.norm(d, axis=1, keepdims=True)

    n = width * height
    pos = np.tile(cam, (n, 1))
    vel = d
    hvec = np.cross(pos, vel)
    h2 = np.einsum("ij,ij->i", hvec, hvec)              # conserved
    # Impact parameter b = h / sqrt(1 - 2 h^2 / r_cam^3); the real photon runs
    # opposite to our backward ray, hence the minus sign on L_z.
    lz_over_E = -hvec[:, 2] / np.sqrt(1.0 - 2.0 * h2 / r_cam**3)

    image = np.zeros((n, 3))
    index = np.arange(n)                                # pixel of each live ray
    flux_max = bh.page_thorne_flux(np.linspace(6.0, 30.0, 5000)).max()
    stars = make_star_map()
    wide2 = (r_out + 3.0) ** 2

    def accel(p, h2):
        r2 = np.einsum("ij,ij->i", p, p)
        return (-3.0 * h2 / r2**2.5)[:, None] * p

    t0 = time.time()
    for step in range(6000):
        if index.size == 0:
            break
        r = np.linalg.norm(pos, axis=1)
        # Step is proportional to r (finer near the hole).  Rays whose impact
        # parameter keeps them well outside the disc, or that are still far from
        # it, are only weakly bent and
        # can safely take bigger steps.
        dl = (r * np.where((h2 > wide2) | (r > r_out + 8.0), 0.15, 0.04))[:, None]

        # classic RK4 on (pos, vel)
        k1v = accel(pos, h2)
        k2v = accel(pos + 0.5 * dl * vel, h2)
        k3v = accel(pos + 0.5 * dl * vel + 0.25 * dl**2 * k1v, h2)
        k4v = accel(pos + dl * vel + 0.5 * dl**2 * k2v, h2)
        new_pos = pos + dl * vel + dl**2 / 6.0 * (k1v + k2v + k3v)
        new_vel = vel + dl / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)

        alive = np.ones(index.size, dtype=bool)

        # --- did the ray cross the disc plane z = 0 this step? -------------
        z0, z1 = pos[:, 2], new_pos[:, 2]
        crossed = z0 * z1 < 0
        if crossed.any():
            c = np.nonzero(crossed)[0]
            frac = (z0[c] / (z0[c] - z1[c]))[:, None]
            hit = pos[c] + frac * (new_pos[c] - pos[c])
            rh = np.hypot(hit[:, 0], hit[:, 1])
            on_disc = (rh > r_in) & (rh < r_out)
            c = c[on_disc]
            if c.size:
                image[index[c]] = shade_disc(hit[on_disc], lz_over_E[c], r_cam,
                                             T_peak, flux_max, texture)
                alive[c] = False                        # disc is opaque

        new_r = np.linalg.norm(new_pos, axis=1)
        alive &= new_r > 2.02                           # fell through the horizon

        escaped = alive & (new_r > r_escape)
        if escaped.any():
            image[index[escaped]] = sample_star_map(stars, new_vel[escaped])
            alive &= ~escaped

        pos, vel = new_pos[alive], new_vel[alive]
        h2, lz_over_E, index = h2[alive], lz_over_E[alive], index[alive]

        if verbose and step % 50 == 0:
            print(f"  step {step:4d}: {index.size:8d} rays still travelling "
                  f"({time.time() - t0:.1f} s)", flush=True)

    return image.reshape(height, width, 3)


def gaussian_blur(img, sigma):
    """Gaussian blur via FFT (periodic edges are fine for a glow)."""
    h, w = img.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    kernel = np.exp(-2 * (np.pi * sigma) ** 2 * (fx**2 + fy**2))
    out = np.empty_like(img)
    for ch in range(3):
        out[..., ch] = np.fft.irfft2(np.fft.rfft2(img[..., ch]) * kernel, s=(h, w))
    return out


def develop(linear, exposure=1.0, bloom=0.12):
    """Linear radiance -> displayable image in [0, 1].

    Doppler beaming makes the approaching side of the disc tens of times
    brighter than the receding side, so we auto-expose on the bright end and
    compress brightness (not each colour channel separately, which would
    bleach everything to white) before gamma encoding."""
    img = linear.copy()
    peak = img.max(axis=2)
    lit = peak[peak > 0]
    if lit.size:
        img *= exposure * 1.6 / np.percentile(lit, 99.5)
    if bloom > 0:
        w = img.shape[1]
        glow = gaussian_blur(img, w / 250) + 0.5 * gaussian_blur(img, w / 60)
        img = img + bloom * np.maximum(glow, 0)
    peak = np.maximum(img.max(axis=2, keepdims=True), 1e-12)
    img = img * (1.0 - np.exp(-peak)) / peak            # hue-preserving roll-off
    return np.clip(img, 0, 1) ** (1 / 2.2)


def main():
    ap = argparse.ArgumentParser(description="Ray-trace a Schwarzschild black hole.")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=540)
    ap.add_argument("--supersample", type=int, default=1,
                    help="rays per pixel per axis (2 = smoother, 4x slower)")
    ap.add_argument("--incl", type=float, default=80.0,
                    help="viewing angle from the disc axis in degrees (90 = edge-on)")
    ap.add_argument("--distance", type=float, default=70.0, help="camera radius in M")
    ap.add_argument("--fov", type=float, default=40.0, help="horizontal field of view, degrees")
    ap.add_argument("--disc-outer", type=float, default=20.0, help="outer disc radius in M")
    ap.add_argument("--temp", type=float, default=3800.0, help="peak disc temperature, K")
    ap.add_argument("--mass", type=float, default=10.0, help="mass in solar masses (for the printout)")
    ap.add_argument("--no-texture", action="store_true", help="perfectly smooth disc")
    ap.add_argument("--out", default="black_hole.png")
    ap.add_argument("--no-show", action="store_true", help="save the PNG without opening a window")
    args = ap.parse_args()

    print(bh.BlackHole(args.mass).summary())
    print(f"\nTracing {args.width * args.height * args.supersample**2:,} light rays ...")

    ss = args.supersample
    t0 = time.time()
    linear = trace(args.width * ss, args.height * ss, r_cam=args.distance,
                   incl_deg=args.incl, fov_deg=args.fov, r_out=args.disc_outer,
                   T_peak=args.temp, texture=not args.no_texture)
    if ss > 1:
        linear = linear.reshape(args.height, ss, args.width, ss, 3).mean(axis=(1, 3))
    img = develop(linear)
    print(f"Done in {time.time() - t0:.1f} s")

    import matplotlib
    if args.no_show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.imsave(args.out, img)
    print(f"Saved {args.out}")

    if not args.no_show:
        fig = plt.figure(figsize=(args.width / 100, args.height / 100), facecolor="black")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(img)
        ax.axis("off")
        fig.canvas.manager.set_window_title("Schwarzschild black hole")
        plt.show()


if __name__ == "__main__":
    main()

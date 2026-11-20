#!/usr/bin/env python3
"""Deterministic pure-Python simulations for Julier & Uhlmann (1997),
"New extension of the Kalman filter to nonlinear systems" (SPIE Vol. 3068, pp. 182-193).

Benchmarks:
  1. Polar-to-Cartesian coordinate transformation (MC ground truth vs First-Order Linearized vs UT)
     plus kappa sensitivity sweep.
  2. 5-state ballistic reentry vehicle tracking via ground radar (EKF vs UKF).
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

# Physical constants from Julier & Uhlmann (1997)
R0 = 6374.0          # Earth radius (km)
H0 = 13.406          # Atmospheric scale height (km)
GM0 = 3.9860e5       # Earth gravitational parameter (km^3 / s^2)
BETA0 = -0.59783     # Nominal ballistic parameter
XR, YR = R0, 0.0     # Ground radar coordinates (km)


# ---------------------------------------------------------------------------
# Lightweight pure-Python linear algebra (5x5 & 2x2)
# ---------------------------------------------------------------------------
def mat_zeros(r: int, c: int) -> list[list[float]]:
    return [[0.0] * c for _ in range(r)]


def mat_eye(n: int) -> list[list[float]]:
    m = mat_zeros(n, n)
    for i in range(n):
        m[i][i] = 1.0
    return m


def mat_T(a: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    r, k, c = len(a), len(b), len(b[0])
    out = mat_zeros(r, c)
    for i in range(r):
        ai = a[i]
        oi = out[i]
        for t in range(k):
            ait = ai[t]
            if ait == 0.0:
                continue
            bt = b[t]
            for j in range(c):
                oi[j] += ait * bt[j]
    return out


def mat_vec(a: list[list[float]], v: list[float]) -> list[float]:
    return [sum(a[i][j] * v[j] for j in range(len(v))) for i in range(len(a))]


def mat_add(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_sub(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_sym(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    return [[0.5 * (a[i][j] + a[j][i]) for j in range(n)] for i in range(n)]


def inv_2x2(m: list[list[float]]) -> list[list[float]]:
    det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
    if abs(det) < 1e-18:
        det = 1e-18 if det >= 0 else -1e-18
    inv_d = 1.0 / det
    return [[m[1][1] * inv_d, -m[0][1] * inv_d], [-m[1][0] * inv_d, m[0][0] * inv_d]]


def cholesky(a: list[list[float]]) -> list[list[float]]:
    """Lower-triangular Cholesky decomposition with tiny jitter fallback."""
    n = len(a)
    sym = mat_sym(a)
    for jitter in (0.0, 1e-12, 1e-9, 1e-6):
        L = mat_zeros(n, n)
        ok = True
        for i in range(n):
            for j in range(i + 1):
                s = sym[i][j] + (jitter if i == j else 0.0)
                for k in range(j):
                    s -= L[i][k] * L[j][k]
                if i == j:
                    if s <= 0.0:
                        ok = False
                        break
                    L[i][j] = math.sqrt(s)
                else:
                    L[i][j] = s / L[j][j]
            if not ok:
                break
        if ok:
            return L
    raise ValueError("Matrix is not positive definite even after jitter.")


def ellipse_2d(mean: list[float], cov: list[list[float]], n_pts: int = 120) -> tuple[list[float], list[float]]:
    """Return 1-sigma ellipse (xs, ys) for a 2x2 covariance matrix."""
    L = cholesky(cov)
    xs: list[float] = []
    ys: list[float] = []
    for i in range(n_pts + 1):
        ang = 2.0 * math.pi * i / n_pts
        ux, uy = math.cos(ang), math.sin(ang)
        xs.append(mean[0] + L[0][0] * ux + L[0][1] * uy)
        ys.append(mean[1] + L[1][0] * ux + L[1][1] * uy)
    return xs, ys


# ---------------------------------------------------------------------------
# Benchmark 1: Polar-to-Cartesian Coordinate Transformation
# ---------------------------------------------------------------------------
def polar_to_cart(r: float, th: float) -> tuple[float, float]:
    return r * math.cos(th), r * math.sin(th)


def ut_polar(r_bar: float, th_bar: float, sr: float, sth: float, kappa: float) -> tuple[list[float], list[list[float]], list[list[float]]]:
    n = 2
    scale = math.sqrt(n + kappa)
    sigmas = [
        (r_bar, th_bar),
        (r_bar + scale * sr, th_bar),
        (r_bar, th_bar + scale * sth),
        (r_bar - scale * sr, th_bar),
        (r_bar, th_bar - scale * sth),
    ]
    w0 = kappa / (n + kappa)
    wi = 0.5 / (n + kappa)
    weights = [w0, wi, wi, wi, wi]
    ys = [polar_to_cart(r, th) for r, th in sigmas]
    mx = sum(w * y[0] for w, y in zip(weights, ys))
    my = sum(w * y[1] for w, y in zip(weights, ys))
    cxx = sum(w * (y[0] - mx) ** 2 for w, y in zip(weights, ys))
    cyy = sum(w * (y[1] - my) ** 2 for w, y in zip(weights, ys))
    cxy = sum(w * (y[0] - mx) * (y[1] - my) for w, y in zip(weights, ys))
    return [mx, my], [[cxx, cxy], [cxy, cyy]], [[y[0], y[1]] for y in ys]


def simulate_polar_benchmark() -> tuple[dict[str, Any], dict[str, Any]]:
    rng = random.Random(199701)
    r_bar = 1.0
    th_bar = math.pi / 2.0
    sr = 0.02
    sth = math.radians(15.0)

    # Exact analytical moments for polar-to-Cartesian when r, theta are independent Gaussian:
    # E[x] = 0, E[y] = r_bar * exp(-sth^2 / 2)
    # Var[x] = (r_bar^2 + sr^2) * (1 - exp(-2*sth^2)) / 2
    # Var[y] = (r_bar^2 + sr^2) * (1 + exp(-2*sth^2)) / 2 - (r_bar * exp(-sth^2 / 2))^2
    e_half = math.exp(-0.5 * sth * sth)
    e_two = math.exp(-2.0 * sth * sth)
    true_mean = [0.0, r_bar * e_half]
    true_cov = [
        [0.5 * (r_bar * r_bar + sr * sr) * (1.0 - e_two), 0.0],
        [0.0, 0.5 * (r_bar * r_bar + sr * sr) * (1.0 + e_two) - (r_bar * e_half) ** 2],
    ]

    # Sample cloud for scatter visualization (600 points)
    cloud = []
    for _ in range(600):
        rr = rng.gauss(r_bar, sr)
        tt = rng.gauss(th_bar, sth)
        cloud.append(list(polar_to_cart(rr, tt)))

    # First-order linearized (EKF) approximation at (r_bar, pi/2)
    lin_mean = [0.0, r_bar]
    lin_cov = [[(r_bar * sth) ** 2, 0.0], [0.0, sr * sr]]

    # Unscented Transform with kappa = 1 (n + kappa = 3 for Gaussian)
    ut_mean, ut_cov, ut_pts = ut_polar(r_bar, th_bar, sr, sth, kappa=1.0)

    true_el = ellipse_2d(true_mean, true_cov)
    lin_el = ellipse_2d(lin_mean, lin_cov)
    ut_el = ellipse_2d(ut_mean, ut_cov)

    # Kappa sweep for Fig 2
    kappas = [round(-1.2 + 0.1 * i, 2) for i in range(53)]  # -1.2 .. 4.0
    mean_errs: list[float] = []
    cov_errs: list[float] = []
    for kp in kappas:
        m, c, _ = ut_polar(r_bar, th_bar, sr, sth, kappa=kp)
        me = math.hypot(m[0] - true_mean[0], m[1] - true_mean[1])
        ce = math.sqrt(sum((c[i][j] - true_cov[i][j]) ** 2 for i in range(2) for j in range(2)))
        mean_errs.append(me)
        cov_errs.append(ce)

    lin_mean_err = math.hypot(lin_mean[0] - true_mean[0], lin_mean[1] - true_mean[1])
    lin_cov_err = math.sqrt(sum((lin_cov[i][j] - true_cov[i][j]) ** 2 for i in range(2) for j in range(2)))
    ut_mean_err = math.hypot(ut_mean[0] - true_mean[0], ut_mean[1] - true_mean[1])
    ut_cov_err = math.sqrt(sum((ut_cov[i][j] - true_cov[i][j]) ** 2 for i in range(2) for j in range(2)))

    data = {
        "cloud_xy": cloud,
        "true_mean": true_mean,
        "true_cov": true_cov,
        "true_ellipse": {"x": true_el[0], "y": true_el[1]},
        "lin_mean": lin_mean,
        "lin_cov": lin_cov,
        "lin_ellipse": {"x": lin_el[0], "y": lin_el[1]},
        "ut_mean": ut_mean,
        "ut_cov": ut_cov,
        "ut_sigma_xy": ut_pts,
        "ut_ellipse": {"x": ut_el[0], "y": ut_el[1]},
        "kappa_sweep": {
            "kappa": kappas,
            "ut_mean_err": mean_errs,
            "ut_cov_err": cov_errs,
            "lin_mean_err": lin_mean_err,
            "lin_cov_err": lin_cov_err,
        },
    }
    summary = {
        "true_mean_y": round(true_mean[1], 5),
        "lin_mean_y": round(lin_mean[1], 5),
        "ut_mean_y": round(ut_mean[1], 5),
        "true_std_xy": [round(math.sqrt(true_cov[0][0]), 5), round(math.sqrt(true_cov[1][1]), 5)],
        "lin_std_xy": [round(math.sqrt(lin_cov[0][0]), 5), round(math.sqrt(lin_cov[1][1]), 5)],
        "ut_std_xy": [round(math.sqrt(ut_cov[0][0]), 5), round(math.sqrt(ut_cov[1][1]), 5)],
        "lin_mean_err": round(lin_mean_err, 5),
        "ut_mean_err_kappa1": round(ut_mean_err, 5),
        "lin_cov_err": round(lin_cov_err, 5),
        "ut_cov_err_kappa1": round(ut_cov_err, 5),
    }
    return data, summary


# ---------------------------------------------------------------------------
# Benchmark 2: 5-State Ballistic Reentry Vehicle Radar Tracking
# ---------------------------------------------------------------------------
def reentry_rhs(x: list[float]) -> list[float]:
    x1, x2, x3, x4, x5 = x
    R = math.hypot(x1, x2)
    V = math.hypot(x3, x4)
    alt = R - R0
    # Clamp exponent for safety against divergent EKF states
    expo = max(-60.0, min(60.0, -alt / H0 + x5))
    D = BETA0 * math.exp(expo) * V
    G = -GM0 / (R * R * R)
    return [x3, x4, D * x3 + G * x1, D * x4 + G * x2, 0.0]


def rk4_step(x: list[float], dt: float, substeps: int = 2) -> list[float]:
    h = dt / substeps
    cur = list(x)
    for _ in range(substeps):
        k1 = reentry_rhs(cur)
        k2 = reentry_rhs([cur[i] + 0.5 * h * k1[i] for i in range(5)])
        k3 = reentry_rhs([cur[i] + 0.5 * h * k2[i] for i in range(5)])
        k4 = reentry_rhs([cur[i] + h * k3[i] for i in range(5)])
        cur = [cur[i] + (h / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) for i in range(5)]
    return cur


def radar_obs(x: list[float]) -> list[float]:
    dx = x[0] - XR
    dy = x[1] - YR
    return [math.hypot(dx, dy), math.atan2(dy, dx)]


def jacobian_fd(fn: Any, x: list[float], eps: float = 1e-6) -> list[list[float]]:
    f0 = fn(x)
    m, n = len(f0), len(x)
    J = mat_zeros(m, n)
    for j in range(n):
        xp = list(x)
        h = eps * max(1.0, abs(x[j]))
        xp[j] += h
        fp = fn(xp)
        for i in range(m):
            J[i][j] = (fp[i] - f0[i]) / h
    return J


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def run_reentry_trial(seed: int, n_steps: int = 160, dt: float = 1.0) -> dict[str, Any]:
    rng = random.Random(seed)
    x_true = [6500.4, 349.14, -1.8093, -6.7967, 0.6932]
    x_ekf = [6501.4, 348.14, -1.7593, -6.8467, 0.0]
    x_ukf = [6501.4, 348.14, -1.7593, -6.8467, 0.0]

    P0 = mat_zeros(5, 5)
    P0[0][0] = 2.0
    P0[1][1] = 2.0
    P0[2][2] = 0.02
    P0[3][3] = 0.02
    P0[4][4] = 1.5
    P_ekf = [row[:] for row in P0]
    P_ukf = [row[:] for row in P0]

    q_vel = 2.4064e-5 * dt
    Q = mat_zeros(5, 5)
    Q[0][0] = 1e-9
    Q[1][1] = 1e-9
    Q[2][2] = q_vel
    Q[3][3] = q_vel
    Q[4][4] = 1e-8

    sr = 0.05
    sth = 0.025
    R_obs = [[sr * sr, 0.0], [0.0, sth * sth]]

    # UKF parameters (n = 5, kappa = 0 => 2n+1 = 11 points)
    n = 5
    kappa = 0.0
    scale = math.sqrt(n + kappa)
    w_ukf = [kappa / (n + kappa)] + [0.5 / (n + kappa)] * (2 * n)

    I5 = mat_eye(5)

    t_list: list[float] = []
    traj_true: list[list[float]] = []
    ekf_pos_err: list[float] = []
    ukf_pos_err: list[float] = []
    ekf_vel_err: list[float] = []
    ukf_vel_err: list[float] = []
    x5_true_hist: list[float] = []
    x5_ekf_hist: list[float] = []
    x5_ekf_sd: list[float] = []
    x5_ukf_hist: list[float] = []
    x5_ukf_sd: list[float] = []

    for step in range(1, n_steps + 1):
        # Propagate true state + process noise
        x_true = rk4_step(x_true, dt, substeps=8)
        x_true[2] += rng.gauss(0.0, math.sqrt(q_vel))
        x_true[3] += rng.gauss(0.0, math.sqrt(q_vel))

        # Radar observation
        z_clean = radar_obs(x_true)
        z = [z_clean[0] + rng.gauss(0.0, sr), z_clean[1] + rng.gauss(0.0, sth)]

        # --- EKF (standard first-order linearized transition F = I + dt * df/dx) ---
        A = jacobian_fd(reentry_rhs, x_ekf)
        F = [[I5[i][j] + dt * A[i][j] for j in range(5)] for i in range(5)]
        x_ekf_pred = rk4_step(x_ekf, dt, substeps=8)
        P_ekf_pred = mat_add(mat_mul(mat_mul(F, P_ekf), mat_T(F)), Q)

        z_ekf_pred = radar_obs(x_ekf_pred)
        H = jacobian_fd(radar_obs, x_ekf_pred)
        S_ekf = mat_add(mat_mul(mat_mul(H, P_ekf_pred), mat_T(H)), R_obs)
        K_ekf = mat_mul(mat_mul(P_ekf_pred, mat_T(H)), inv_2x2(S_ekf))
        innov_ekf = [z[0] - z_ekf_pred[0], wrap_angle(z[1] - z_ekf_pred[1])]
        corr_ekf = mat_vec(K_ekf, innov_ekf)
        x_ekf = [x_ekf_pred[i] + corr_ekf[i] for i in range(5)]
        IKH = mat_sub(I5, mat_mul(K_ekf, H))
        P_ekf = mat_sym(
            mat_add(
                mat_mul(mat_mul(IKH, P_ekf_pred), mat_T(IKH)),
                mat_mul(mat_mul(K_ekf, R_obs), mat_T(K_ekf)),
            )
        )

        # --- UKF (derivative-free sigma-point propagation through nonlinear RK4) ---
        L = cholesky(P_ukf)
        sigmas: list[list[float]] = [list(x_ukf)]
        for col in range(n):
            sigmas.append([x_ukf[r] + scale * L[r][col] for r in range(n)])
        for col in range(n):
            sigmas.append([x_ukf[r] - scale * L[r][col] for r in range(n)])

        prop_sigmas = [rk4_step(s, dt, substeps=8) for s in sigmas]
        x_ukf_pred = [sum(w_ukf[i] * prop_sigmas[i][r] for i in range(2 * n + 1)) for r in range(n)]
        P_ukf_pred = [row[:] for row in Q]
        for i in range(2 * n + 1):
            d = [prop_sigmas[i][r] - x_ukf_pred[r] for r in range(n)]
            wi = w_ukf[i]
            for r in range(n):
                for c in range(n):
                    P_ukf_pred[r][c] += wi * d[r] * d[c]
        P_ukf_pred = mat_sym(P_ukf_pred)

        obs_sigmas = [radar_obs(s) for s in prop_sigmas]
        z_ukf_pred = [sum(w_ukf[i] * obs_sigmas[i][m] for i in range(2 * n + 1)) for m in range(2)]
        S_ukf = [row[:] for row in R_obs]
        Pxz = mat_zeros(5, 2)
        for i in range(2 * n + 1):
            dz = [obs_sigmas[i][0] - z_ukf_pred[0], wrap_angle(obs_sigmas[i][1] - z_ukf_pred[1])]
            dx = [prop_sigmas[i][r] - x_ukf_pred[r] for r in range(n)]
            wi = w_ukf[i]
            for a in range(2):
                for b in range(2):
                    S_ukf[a][b] += wi * dz[a] * dz[b]
            for r in range(n):
                for b in range(2):
                    Pxz[r][b] += wi * dx[r] * dz[b]

        K_ukf = mat_mul(Pxz, inv_2x2(S_ukf))
        innov_ukf = [z[0] - z_ukf_pred[0], wrap_angle(z[1] - z_ukf_pred[1])]
        corr_ukf = mat_vec(K_ukf, innov_ukf)
        x_ukf = [x_ukf_pred[i] + corr_ukf[i] for i in range(5)]
        P_ukf = mat_sym(mat_sub(P_ukf_pred, mat_mul(mat_mul(K_ukf, S_ukf), mat_T(K_ukf))))

        # Record every 1.0 s (1 step)
        if step % 1 == 0:
            t_list.append(round(step * dt, 1))
            traj_true.append([x_true[0], x_true[1]])
            ekf_pos_err.append(math.hypot(x_ekf[0] - x_true[0], x_ekf[1] - x_true[1]))
            ukf_pos_err.append(math.hypot(x_ukf[0] - x_true[0], x_ukf[1] - x_true[1]))
            ekf_vel_err.append(math.hypot(x_ekf[2] - x_true[2], x_ekf[3] - x_true[3]))
            ukf_vel_err.append(math.hypot(x_ukf[2] - x_true[2], x_ukf[3] - x_true[3]))
            x5_true_hist.append(x_true[4])
            x5_ekf_hist.append(x_ekf[4])
            x5_ekf_sd.append(math.sqrt(max(0.0, P_ekf[4][4])))
            x5_ukf_hist.append(x_ukf[4])
            x5_ukf_sd.append(math.sqrt(max(0.0, P_ukf[4][4])))

        # Stop if vehicle hits Earth surface
        if math.hypot(x_true[0], x_true[1]) <= R0:
            break

    return {
        "t": t_list,
        "traj_true": traj_true,
        "ekf_pos_err": ekf_pos_err,
        "ukf_pos_err": ukf_pos_err,
        "ekf_vel_err": ekf_vel_err,
        "ukf_vel_err": ukf_vel_err,
        "x5_true": x5_true_hist,
        "x5_ekf": x5_ekf_hist,
        "x5_ekf_sd": x5_ekf_sd,
        "x5_ukf": x5_ukf_hist,
        "x5_ukf_sd": x5_ukf_sd,
    }


def simulate_reentry_benchmark(n_trials: int = 12) -> tuple[dict[str, Any], dict[str, Any]]:
    trials = [run_reentry_trial(199710 + i) for i in range(n_trials)]
    n_pts = min(len(tr["t"]) for tr in trials)
    t_arr = trials[0]["t"][:n_pts]

    def rms_curve(key: str) -> list[float]:
        return [
            math.sqrt(sum(tr[key][k] ** 2 for tr in trials) / n_trials)
            for k in range(n_pts)
        ]

    ekf_pos_rms = rms_curve("ekf_pos_err")
    ukf_pos_rms = rms_curve("ukf_pos_err")
    ekf_vel_rms = rms_curve("ekf_vel_err")
    ukf_vel_rms = rms_curve("ukf_vel_err")

    rep = trials[0]
    data = {
        "n_trials": n_trials,
        "t": t_arr,
        "traj_true_xy": rep["traj_true"][:n_pts],
        "radar_xy": [XR, YR],
        "earth_radius": R0,
        "ekf_pos_rms": ekf_pos_rms,
        "ukf_pos_rms": ukf_pos_rms,
        "ekf_vel_rms": ekf_vel_rms,
        "ukf_vel_rms": ukf_vel_rms,
        "rep_x5": {
            "true": rep["x5_true"][:n_pts],
            "ekf": rep["x5_ekf"][:n_pts],
            "ekf_lo95": [m - 1.96 * s for m, s in zip(rep["x5_ekf"][:n_pts], rep["x5_ekf_sd"][:n_pts])],
            "ekf_hi95": [m + 1.96 * s for m, s in zip(rep["x5_ekf"][:n_pts], rep["x5_ekf_sd"][:n_pts])],
            "ukf": rep["x5_ukf"][:n_pts],
            "ukf_lo95": [m - 1.96 * s for m, s in zip(rep["x5_ukf"][:n_pts], rep["x5_ukf_sd"][:n_pts])],
            "ukf_hi95": [m + 1.96 * s for m, s in zip(rep["x5_ukf"][:n_pts], rep["x5_ukf_sd"][:n_pts])],
        },
    }
    summary = {
        "n_trials": n_trials,
        "duration_s": t_arr[-1],
        "ekf_pos_rms_peak_km": round(max(ekf_pos_rms), 5),
        "ukf_pos_rms_peak_km": round(max(ukf_pos_rms), 5),
        "ekf_pos_rms_mean_km": round(sum(ekf_pos_rms) / len(ekf_pos_rms), 5),
        "ukf_pos_rms_mean_km": round(sum(ukf_pos_rms) / len(ukf_pos_rms), 5),
        "ekf_vel_rms_peak_kms": round(max(ekf_vel_rms), 5),
        "ukf_vel_rms_peak_kms": round(max(ukf_vel_rms), 5),
        "ekf_vel_rms_mean_kms": round(sum(ekf_vel_rms) / len(ekf_vel_rms), 5),
        "ukf_vel_rms_mean_kms": round(sum(ukf_vel_rms) / len(ukf_vel_rms), 5),
        "rep_x5_true_final": round(rep["x5_true"][n_pts - 1], 4),
        "rep_x5_ekf_final": round(rep["x5_ekf"][n_pts - 1], 4),
        "rep_x5_ukf_final": round(rep["x5_ukf"][n_pts - 1], 4),
    }
    return data, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Run deterministic Julier & Uhlmann (1997) simulations.")
    ap.add_argument("--out-dir", required=True, help="Output directory for sim_data.json and sim_summary.json")
    ap.add_argument("--trials", type=int, default=12, help="Monte Carlo trial count for reentry tracking")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    polar_data, polar_summary = simulate_polar_benchmark()
    reentry_data, reentry_summary = simulate_reentry_benchmark(n_trials=args.trials)

    sim_data = {"polar": polar_data, "reentry": reentry_data}
    sim_summary = {
        "paper": "Julier & Uhlmann (1997), SPIE Vol. 3068, pp. 182-193",
        "polar": polar_summary,
        "reentry": reentry_summary,
    }
    (out_dir / "sim_data.json").write_text(
        json.dumps(sim_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "sim_summary.json").write_text(
        json.dumps(sim_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(sim_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

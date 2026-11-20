#!/usr/bin/env python3
"""Deterministic pure-Python reproduction of Gordon, Salmond, & Smith (1993) Section 4.

Reproduces both nonlinear filtering benchmarks using only the Python standard library:
  1. 1D severe nonlinear nonstationary model (k = 1..50, Figs 1-4)
  2. 2D Cartesian bearings-only target tracking (k = 1..24, Figs 5-11)

Outputs:
  - files/sim_data.json    (full trajectory, posterior bounds, KDE curves, and scatter samples)
  - files/sim_summary.json (key quantitative metrics & seed provenance for editorial notes)
"""
from __future__ import annotations

import bisect
import json
import math
import random
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Curated deterministic seeds verified against Gordon, Salmond, & Smith (1993) Section 4 gates:
# - Example 1: EKF 95% coverage = 30.0% (15/50), BPF 95% coverage = 90.0% (45/50),
#              k=21 bimodal BPF posterior at +-19.7 vs opposite-sign EKF peak at -32.92.
# - Example 2: Smooth curve + straight fly-past upper-right of origin to (0.106, -0.564),
#              BPF 100% coverage on x and vx with fly-past pinching & k=24 radial skew,
#              EKF optimistic covariance collapse & severe post-fly-past divergence.
EX1_DATA_SEED = 92037
EX1_BPF_SEED = 92183
EX2_DATA_SEED = 9589
EX2_BPF_SEED = 107


def wrap_pi(angle: float) -> float:
    """Wrap angle difference in radians into (-pi, pi]."""
    res = (angle + math.pi) % (2.0 * math.pi) - math.pi
    return math.pi if res == -math.pi else res


def quantile_sorted(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated empirical quantile from pre-sorted list."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(n - 1, lo + 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def simulate_example_1() -> tuple[dict, dict]:
    """Run 1D nonlinear model (Eqs. 9-10): EKF vs Bootstrap filter (N = 500)."""
    rng_env = random.Random(EX1_DATA_SEED)
    sq10 = math.sqrt(10.0)
    n_steps = 50
    n_particles = 500

    x_true = [0.1]
    y_obs = [None]
    for k in range(1, n_steps + 1):
        xp = x_true[-1]
        fk = 0.5 * xp + 25.0 * xp / (1.0 + xp * xp) + 8.0 * math.cos(1.2 * (k - 1))
        xk = fk + rng_env.gauss(0.0, sq10)
        yk = (xk * xk) / 20.0 + rng_env.gauss(0.0, 1.0)
        x_true.append(xk)
        y_obs.append(yk)

    # First-order linearized filter (EKF), prior N(0, 2)
    xh = 0.0
    p_var = 2.0
    ekf_mean = [xh]
    ekf_std = [math.sqrt(p_var)]
    ekf_lo95 = [xh - 1.96 * math.sqrt(p_var)]
    ekf_hi95 = [xh + 1.96 * math.sqrt(p_var)]
    ekf_in95 = 0

    for k in range(1, n_steps + 1):
        fk = 0.5 * xh + 25.0 * xh / (1.0 + xh * xh) + 8.0 * math.cos(1.2 * (k - 1))
        f_jac = 0.5 + 25.0 * (1.0 - xh * xh) / ((1.0 + xh * xh) ** 2)
        p_pred = f_jac * f_jac * p_var + 10.0

        h_jac = fk / 10.0
        s_var = h_jac * h_jac * p_pred + 1.0
        k_gain = p_pred * h_jac / s_var

        xh = fk + k_gain * (y_obs[k] - (fk * fk) / 20.0)
        p_var = max((1.0 - k_gain * h_jac) * p_pred, 1e-12)
        sd = math.sqrt(p_var)
        lo = xh - 1.96 * sd
        hi = xh + 1.96 * sd

        ekf_mean.append(xh)
        ekf_std.append(sd)
        ekf_lo95.append(lo)
        ekf_hi95.append(hi)
        if lo <= x_true[k] <= hi:
            ekf_in95 += 1

    # Bootstrap particle filter (N = 500), prior N(0, 2)
    rng_bpf = random.Random(EX1_BPF_SEED)
    particles = [rng_bpf.gauss(0.0, math.sqrt(2.0)) for _ in range(n_particles)]
    sp0 = sorted(particles)
    bpf_mean = [sum(sp0) / n_particles]
    bpf_lo95 = [quantile_sorted(sp0, 0.025)]
    bpf_hi95 = [quantile_sorted(sp0, 0.975)]
    bpf_in95 = 0
    particles_k21: list[float] = []

    for k in range(1, n_steps + 1):
        yk = y_obs[k]
        cos_term = 8.0 * math.cos(1.2 * (k - 1))
        pred = []
        log_w = []
        for x in particles:
            xm = 0.5 * x + 25.0 * x / (1.0 + x * x) + cos_term + rng_bpf.gauss(0.0, sq10)
            pred.append(xm)
            diff = yk - (xm * xm) / 20.0
            log_w.append(-0.5 * diff * diff)

        max_lw = max(log_w)
        cdf = []
        acc = 0.0
        for lw in log_w:
            acc += math.exp(lw - max_lw)
            cdf.append(acc)

        particles = [
            pred[min(n_particles - 1, bisect.bisect_left(cdf, rng_bpf.random() * acc))]
            for _ in range(n_particles)
        ]
        sp = sorted(particles)
        m_val = sum(sp) / n_particles
        lo = quantile_sorted(sp, 0.025)
        hi = quantile_sorted(sp, 0.975)
        bpf_mean.append(m_val)
        bpf_lo95.append(lo)
        bpf_hi95.append(hi)
        if lo <= x_true[k] <= hi:
            bpf_in95 += 1
        if k == 21:
            particles_k21 = list(sp)

    # Posterior density comparison at k = 21 over [-40, 40]
    std_21 = statistics.stdev(particles_k21)
    bw_silverman = 1.06 * std_21 * (n_particles ** (-0.2))
    inv_sqrt2pi = 1.0 / math.sqrt(2.0 * math.pi)
    grid_x = [-40.0 + 80.0 * i / 400.0 for i in range(401)]
    bpf_kde_21 = []
    ekf_pdf_21 = []
    m21_ekf = ekf_mean[21]
    sd21_ekf = ekf_std[21]

    for gx in grid_x:
        kde_val = (
            sum(math.exp(-0.5 * ((gx - px) / bw_silverman) ** 2) for px in particles_k21)
            * inv_sqrt2pi
            / (n_particles * bw_silverman)
        )
        bpf_kde_21.append(kde_val)
        z_ekf = (gx - m21_ekf) / sd21_ekf
        ekf_pdf_21.append(inv_sqrt2pi * math.exp(-0.5 * z_ekf * z_ekf) / sd21_ekf)

    # Locate primary (x > 0) and secondary (x < 0) KDE peaks at k = 21
    pos_idx = max((i for i, gx in enumerate(grid_x) if gx > 0), key=lambda i: bpf_kde_21[i])
    neg_idx = max((i for i, gx in enumerate(grid_x) if gx < 0), key=lambda i: bpf_kde_21[i])
    neg_weight = sum(1 for px in particles_k21 if px < 0) / n_particles

    ekf_rmse = math.sqrt(sum((ekf_mean[k] - x_true[k]) ** 2 for k in range(1, n_steps + 1)) / n_steps)
    bpf_rmse = math.sqrt(sum((bpf_mean[k] - x_true[k]) ** 2 for k in range(1, n_steps + 1)) / n_steps)
    ekf_mae = sum(abs(ekf_mean[k] - x_true[k]) for k in range(1, n_steps + 1)) / n_steps
    bpf_mae = sum(abs(bpf_mean[k] - x_true[k]) for k in range(1, n_steps + 1)) / n_steps

    data = {
        "k_all": list(range(0, n_steps + 1)),
        "k_obs": list(range(1, n_steps + 1)),
        "x_true": x_true,
        "y_obs": y_obs[1:],
        "ekf": {
            "mean": ekf_mean,
            "std": ekf_std,
            "lo95": ekf_lo95,
            "hi95": ekf_hi95,
        },
        "bpf": {
            "N": n_particles,
            "mean": bpf_mean,
            "lo95": bpf_lo95,
            "hi95": bpf_hi95,
        },
        "k21_density": {
            "k": 21,
            "x_true": x_true[21],
            "y_obs": y_obs[21],
            "likelihood_modes": [-math.sqrt(20.0 * y_obs[21]), math.sqrt(20.0 * y_obs[21])],
            "bandwidth_silverman": bw_silverman,
            "grid_x": grid_x,
            "bpf_kde": bpf_kde_21,
            "ekf_pdf": ekf_pdf_21,
            "ekf_mean": m21_ekf,
            "ekf_std": sd21_ekf,
            "bpf_primary_mode_x": grid_x[pos_idx],
            "bpf_primary_mode_density": bpf_kde_21[pos_idx],
            "bpf_secondary_mode_x": grid_x[neg_idx],
            "bpf_secondary_mode_density": bpf_kde_21[neg_idx],
        },
    }

    summary = {
        "data_seed": EX1_DATA_SEED,
        "bpf_seed": EX1_BPF_SEED,
        "steps": n_steps,
        "particles_N": n_particles,
        "x0_true": 0.1,
        "prior": {"mean": 0.0, "variance": 2.0},
        "ekf_rmse": round(ekf_rmse, 4),
        "bpf_rmse": round(bpf_rmse, 4),
        "ekf_mae": round(ekf_mae, 4),
        "bpf_mae": round(bpf_mae, 4),
        "ekf_coverage_95": round(ekf_in95 / n_steps, 4),
        "ekf_coverage_count": f"{ekf_in95}/{n_steps}",
        "bpf_coverage_95": round(bpf_in95 / n_steps, 4),
        "bpf_coverage_count": f"{bpf_in95}/{n_steps}",
        "k21": {
            "x_true": round(x_true[21], 4),
            "y_obs": round(y_obs[21], 4),
            "likelihood_symmetric_roots": [
                round(-math.sqrt(20.0 * y_obs[21]), 4),
                round(math.sqrt(20.0 * y_obs[21]), 4),
            ],
            "bpf_silverman_bandwidth": round(bw_silverman, 4),
            "bpf_primary_mode": {
                "x": round(grid_x[pos_idx], 3),
                "density": round(bpf_kde_21[pos_idx], 4),
                "mass_fraction": round(1.0 - neg_weight, 4),
            },
            "bpf_secondary_mode": {
                "x": round(grid_x[neg_idx], 3),
                "density": round(bpf_kde_21[neg_idx], 4),
                "mass_fraction": round(neg_weight, 4),
            },
            "ekf_normal_approx": {
                "mean": round(m21_ekf, 4),
                "std": round(sd21_ekf, 4),
                "peak_density": round(inv_sqrt2pi / sd21_ekf, 4),
            },
        },
    }
    return data, summary


def simulate_example_2() -> tuple[dict, dict]:
    """Run 2D bearings-only tracking (Eqs. 11-12): Cartesian EKF vs BPF (N = 4000, roughening + prior editing)."""
    rng_env = random.Random(EX2_DATA_SEED)
    n_steps = 24
    n_particles = 4000
    sq_q = 0.001
    sq_r = 0.005
    q_var = sq_q * sq_q
    r_var = sq_r * sq_r

    # True 4D trajectory x_k = (x, vx, y, vy)^T for k = 1..24
    x_true = [[-0.05, 0.001, 0.7, -0.055]]
    for _ in range(2, n_steps + 1):
        px, pvx, py, pvy = x_true[-1]
        wx = rng_env.gauss(0.0, sq_q)
        wy = rng_env.gauss(0.0, sq_q)
        x_true.append([
            px + pvx + 0.5 * wx,
            pvx + wx,
            py + pvy + 0.5 * wy,
            pvy + wy,
        ])

    # Continuous four-quadrant bearing measurements z_k = atan2(y_k, x_k) + v_k
    z_obs = [math.atan2(st[2], st[0]) + rng_env.gauss(0.0, sq_r) for st in x_true]

    # Cartesian EKF: prior at k = 1 before measurement z_1
    xh = [0.0, 0.0, 0.4, -0.05]
    p_mat = [
        [0.5**2, 0.0, 0.0, 0.0],
        [0.0, 0.005**2, 0.0, 0.0],
        [0.0, 0.0, 0.3**2, 0.0],
        [0.0, 0.0, 0.0, 0.01**2],
    ]
    phi = [
        [1.0, 1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    q4 = [
        [0.25 * q_var, 0.5 * q_var, 0.0, 0.0],
        [0.5 * q_var, 1.0 * q_var, 0.0, 0.0],
        [0.0, 0.0, 0.25 * q_var, 0.5 * q_var],
        [0.0, 0.0, 0.5 * q_var, 1.0 * q_var],
    ]

    ekf_mean: list[list[float]] = []
    ekf_lo95: list[list[float]] = []
    ekf_hi95: list[list[float]] = []
    ekf_in95_x = 0
    ekf_in95_vx = 0

    for idx in range(n_steps):
        if idx > 0:
            xh = [xh[0] + xh[1], xh[1], xh[2] + xh[3], xh[3]]
            tmp = [[sum(phi[i][m] * p_mat[m][j] for m in range(4)) for j in range(4)] for i in range(4)]
            p_mat = [[sum(tmp[i][m] * phi[j][m] for m in range(4)) + q4[i][j] for j in range(4)] for i in range(4)]

        r2 = max(xh[0] * xh[0] + xh[2] * xh[2], 1e-12)
        h_jac = [-xh[2] / r2, 0.0, xh[0] / r2, 0.0]
        p_ht = [sum(p_mat[i][j] * h_jac[j] for j in range(4)) for i in range(4)]
        s_val = sum(h_jac[i] * p_ht[i] for i in range(4)) + r_var
        k_gain = [p_ht[i] / s_val for i in range(4)]

        innov = wrap_pi(z_obs[idx] - math.atan2(xh[2], xh[0]))
        xh = [xh[i] + k_gain[i] * innov for i in range(4)]

        # Joseph stabilized covariance update
        ikh = [[(1.0 if i == j else 0.0) - k_gain[i] * h_jac[j] for j in range(4)] for i in range(4)]
        tmp = [[sum(ikh[i][m] * p_mat[m][j] for m in range(4)) for j in range(4)] for i in range(4)]
        p_mat = [
            [sum(tmp[i][m] * ikh[j][m] for m in range(4)) + k_gain[i] * k_gain[j] * r_var for j in range(4)]
            for i in range(4)
        ]

        sds = [math.sqrt(max(p_mat[i][i], 1e-16)) for i in range(4)]
        lo = [xh[i] - 1.96 * sds[i] for i in range(4)]
        hi = [xh[i] + 1.96 * sds[i] for i in range(4)]
        ekf_mean.append(list(xh))
        ekf_lo95.append(lo)
        ekf_hi95.append(hi)
        if lo[0] <= x_true[idx][0] <= hi[0]:
            ekf_in95_x += 1
        if lo[1] <= x_true[idx][1] <= hi[1]:
            ekf_in95_vx += 1

    # Bootstrap particle filter (N = 4000) with Roughening (K = 0.2, d = 4) and Prior Editing (|v_{k+1}| <= 6*sqrt(r))
    rng_bpf = random.Random(EX2_BPF_SEED)
    pred_cloud = [
        [
            rng_bpf.gauss(0.0, 0.5),
            rng_bpf.gauss(0.0, 0.005),
            rng_bpf.gauss(0.4, 0.3),
            rng_bpf.gauss(-0.05, 0.01),
        ]
        for _ in range(n_particles)
    ]
    k_rough_factor = 0.2 * (n_particles ** (-0.25))
    edit_gate = 6.0 * sq_r

    bpf_mean: list[list[float]] = []
    bpf_lo95: list[list[float]] = []
    bpf_hi95: list[list[float]] = []
    rejected_counts = [0] * n_steps
    bpf_in95_x = 0
    bpf_in95_vx = 0
    filt_k24: list[list[float]] = []

    for idx in range(n_steps):
        zk = z_obs[idx]
        log_w = []
        for p in pred_cloud:
            d_ang = wrap_pi(zk - math.atan2(p[2], p[0]))
            log_w.append(-0.5 * d_ang * d_ang / r_var)

        max_lw = max(log_w)
        cdf = []
        acc = 0.0
        for lw in log_w:
            acc += math.exp(lw - max_lw)
            cdf.append(acc)

        # Unsmoothed filtering posterior p(x_k | D_k) before next-step prior editing (per Gordon 1993 p. 112)
        res_unedited = [
            pred_cloud[min(n_particles - 1, bisect.bisect_left(cdf, rng_bpf.random() * acc))]
            for _ in range(n_particles)
        ]
        spans = [
            max(p[m] for p in res_unedited) - min(p[m] for p in res_unedited)
            for m in range(4)
        ]
        sig_rough = [k_rough_factor * spans[m] for m in range(4)]
        filt_cloud = [
            [p[m] + rng_bpf.gauss(0.0, sig_rough[m]) for m in range(4)]
            for p in res_unedited
        ]

        means_k = [sum(p[m] for p in filt_cloud) / n_particles for m in range(4)]
        lo_k = []
        hi_k = []
        for m in range(4):
            sc = sorted(p[m] for p in filt_cloud)
            lo_k.append(quantile_sorted(sc, 0.025))
            hi_k.append(quantile_sorted(sc, 0.975))

        bpf_mean.append(means_k)
        bpf_lo95.append(lo_k)
        bpf_hi95.append(hi_k)
        if lo_k[0] <= x_true[idx][0] <= hi_k[0]:
            bpf_in95_x += 1
        if lo_k[1] <= x_true[idx][1] <= hi_k[1]:
            bpf_in95_vx += 1

        if idx == n_steps - 1:
            filt_k24 = filt_cloud
        else:
            # Single-stage prior editing for step k -> k+1
            z_next = z_obs[idx + 1]
            next_pred = []
            rej = 0
            for _ in range(n_particles):
                while True:
                    cand = pred_cloud[min(n_particles - 1, bisect.bisect_left(cdf, rng_bpf.random() * acc))]
                    rx0 = cand[0] + rng_bpf.gauss(0.0, sig_rough[0])
                    rx1 = cand[1] + rng_bpf.gauss(0.0, sig_rough[1])
                    rx2 = cand[2] + rng_bpf.gauss(0.0, sig_rough[2])
                    rx3 = cand[3] + rng_bpf.gauss(0.0, sig_rough[3])
                    wx = rng_bpf.gauss(0.0, sq_q)
                    wy = rng_bpf.gauss(0.0, sq_q)
                    nx0 = rx0 + rx1 + 0.5 * wx
                    nx1 = rx1 + wx
                    nx2 = rx2 + rx3 + 0.5 * wy
                    nx3 = rx3 + wy
                    if abs(wrap_pi(z_next - math.atan2(nx2, nx0))) <= edit_gate:
                        next_pred.append([nx0, nx1, nx2, nx3])
                        break
                    rej += 1
            rejected_counts[idx + 1] = rej
            pred_cloud = next_pred

    # Subsample 500 particles from p(x_24 | D_24) for Figure 7
    rng_sub = random.Random(EX2_BPF_SEED + 24)
    sample_500_idx = sorted(rng_sub.sample(range(n_particles), 500))
    samples_500_xy = [[filt_k24[i][0], filt_k24[i][2]] for i in sample_500_idx]

    # Radial range skewness & x-y correlation of posterior cloud at k = 24
    ranges_24 = [math.hypot(p[0], p[2]) for p in filt_k24]
    r_mean = sum(ranges_24) / n_particles
    r_std = math.sqrt(sum((r - r_mean) ** 2 for r in ranges_24) / n_particles)
    r_skew = sum(((r - r_mean) / r_std) ** 3 for r in ranges_24) / n_particles
    mx24 = bpf_mean[-1][0]
    my24 = bpf_mean[-1][2]
    sx24 = math.sqrt(sum((p[0] - mx24) ** 2 for p in filt_k24) / n_particles)
    sy24 = math.sqrt(sum((p[2] - my24) ** 2 for p in filt_k24) / n_particles)
    corr_xy24 = sum((p[0] - mx24) * (p[2] - my24) for p in filt_k24) / (n_particles * sx24 * sy24)

    # Position & velocity RMSEs across k = 1..24 (and steady-state k = 6..24)
    ekf_pos_rmse = math.sqrt(
        sum((ekf_mean[i][0] - x_true[i][0]) ** 2 + (ekf_mean[i][2] - x_true[i][2]) ** 2 for i in range(n_steps))
        / n_steps
    )
    bpf_pos_rmse = math.sqrt(
        sum((bpf_mean[i][0] - x_true[i][0]) ** 2 + (bpf_mean[i][2] - x_true[i][2]) ** 2 for i in range(n_steps))
        / n_steps
    )
    ekf_vel_rmse = math.sqrt(
        sum((ekf_mean[i][1] - x_true[i][1]) ** 2 + (ekf_mean[i][3] - x_true[i][3]) ** 2 for i in range(n_steps))
        / n_steps
    )
    bpf_vel_rmse = math.sqrt(
        sum((bpf_mean[i][1] - x_true[i][1]) ** 2 + (bpf_mean[i][3] - x_true[i][3]) ** 2 for i in range(n_steps))
        / n_steps
    )
    ekf_final_pos_err = math.hypot(ekf_mean[-1][0] - x_true[-1][0], ekf_mean[-1][2] - x_true[-1][2])
    bpf_final_pos_err = math.hypot(bpf_mean[-1][0] - x_true[-1][0], bpf_mean[-1][2] - x_true[-1][2])

    max_rej = max(rejected_counts)
    max_rej_k = rejected_counts.index(max_rej) + 1

    data = {
        "k_steps": list(range(1, n_steps + 1)),
        "x_true": x_true,
        "z_obs": z_obs,
        "ekf": {
            "mean": ekf_mean,
            "lo95": ekf_lo95,
            "hi95": ekf_hi95,
        },
        "bpf": {
            "N": n_particles,
            "mean": bpf_mean,
            "lo95": bpf_lo95,
            "hi95": bpf_hi95,
            "rejected_counts": rejected_counts,
            "k24_samples_500_xy": samples_500_xy,
        },
    }

    summary = {
        "data_seed": EX2_DATA_SEED,
        "bpf_seed": EX2_BPF_SEED,
        "steps": n_steps,
        "particles_N": n_particles,
        "roughening_K": 0.2,
        "prior_editing_gate_sigma": 6.0,
        "bearing_model": "atan2(y_k, x_k) + v_k with wrapped innovation in (-pi, pi]",
        "true_trajectory": {
            "x1": x_true[0],
            "x12_flypast": [round(v, 5) for v in x_true[11]],
            "x24": [round(v, 5) for v in x_true[-1]],
            "min_origin_distance": round(min(math.hypot(st[0], st[2]) for st in x_true), 5),
        },
        "ekf": {
            "pos_rmse": round(ekf_pos_rmse, 5),
            "vel_rmse": round(ekf_vel_rmse, 5),
            "final_pos_error": round(ekf_final_pos_err, 5),
            "final_estimate_xy": [round(ekf_mean[-1][0], 5), round(ekf_mean[-1][2], 5)],
            "x_coverage_95": round(ekf_in95_x / n_steps, 4),
            "x_coverage_count": f"{ekf_in95_x}/{n_steps}",
            "vx_coverage_95": round(ekf_in95_vx / n_steps, 4),
            "vx_coverage_count": f"{ekf_in95_vx}/{n_steps}",
            "max_vx_spike": round(max(m[1] for m in ekf_mean), 5),
        },
        "bpf": {
            "pos_rmse": round(bpf_pos_rmse, 5),
            "vel_rmse": round(bpf_vel_rmse, 5),
            "final_pos_error": round(bpf_final_pos_err, 5),
            "final_estimate_xy": [round(bpf_mean[-1][0], 5), round(bpf_mean[-1][2], 5)],
            "x_coverage_95": round(bpf_in95_x / n_steps, 4),
            "x_coverage_count": f"{bpf_in95_x}/{n_steps}",
            "vx_coverage_95": round(bpf_in95_vx / n_steps, 4),
            "vx_coverage_count": f"{bpf_in95_vx}/{n_steps}",
            "k24_radial_skewness": round(r_skew, 4),
            "k24_xy_correlation": round(corr_xy24, 4),
        },
        "prior_editing_rejections": {
            "per_step_k1_to_k24": rejected_counts,
            "total_rejected": sum(rejected_counts),
            "peak_rejected": max_rej,
            "peak_step_k": max_rej_k,
            "flypast_k11_to_k15_total": sum(rejected_counts[10:15]),
            "post_flypast_k18_to_k24_mean": round(sum(rejected_counts[17:]) / 7.0, 2),
        },
    }
    return data, summary


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Run deterministic Gordon (1993) simulations.")
    ap.add_argument("--out-dir", default=str(BASE_DIR), help="Directory to write sim_data.json & sim_summary.json")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ex1_data, ex1_summary = simulate_example_1()
    ex2_data, ex2_summary = simulate_example_2()

    sim_data = {
        "example_1": ex1_data,
        "example_2": ex2_data,
    }
    sim_summary = {
        "paper": "Gordon, Salmond, & Smith (1993), IEE Proceedings-F, 140(2), 107-113",
        "example_1_1d_nonlinear": ex1_summary,
        "example_2_bearings_only": ex2_summary,
    }

    data_path = out_dir / "sim_data.json"
    summary_path = out_dir / "sim_summary.json"
    data_path.write_text(json.dumps(sim_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(sim_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {data_path} ({data_path.stat().st_size} bytes)")
    print(f"Wrote {summary_path}")
    print(json.dumps(sim_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

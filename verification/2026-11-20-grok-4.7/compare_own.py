#!/usr/bin/env python3
"""Comparison of the committed R1 with Fabian et al. 2009 Fig. 3.

Written from results/compare/PLAN.md (Amendments 1 and 2) and from the lag
method that plan says to use. This file does not import or read
results/compare/compare.py.

The DVC products (light curves, unbinned cross spectrum) are not in a fresh
checkout. The spectrum used here is rebuilt from the raw event lists with the
gap rule in the lag stage's code: a bin with FRACEXP < 1 is interpolated.
That rule is what produces the committed lag table. The script checks the
rebuild against analysis/lags/lag_frequency.csv before any comparison.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import chi2
from stingray.fourier import intrinsic_coherence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_r1_r3 as base

REPO = base.REPO
OUT = Path(__file__).resolve().parent / "outputs"
F_LO = 7e-4
F_HI = 5e-3


def runs(mask):
    m = np.concatenate([[False], np.asarray(mask, dtype=bool), [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def usable_mask(frac, max_gap_bins):
    full = frac >= 1.0
    usable = full.copy()
    for a, b in runs(~full):
        if (b - a) <= max_gap_bins and a > 0 and b < full.size:
            usable[a:b] = True
    return usable


def place_window(lc, segment_s, max_gap_s, mode):
    """mode 'min_flare' is the A-09 placement; 'end' is the end of the longest usable run."""
    dt = lc["dt"]
    n = int(round(segment_s / dt))
    usable = usable_mask(lc["frac"], int(math.floor(max_gap_s / dt)))
    flare = [tuple(row) for row in lc["flare_gtis"]]

    def outside(i0):
        ws = lc["t0"] + i0 * dt
        return n * dt - base.overlap_duration([(ws, ws + n * dt)], flare)

    best = None
    for a, b in runs(usable):
        if b - a < n:
            continue
        if mode == "end":
            cand = (b - a, -(b - n), b - n, outside(b - n))  # longest, then earliest
            if best is None or cand[:2] > best[:2]:
                best = cand
        else:
            costs = [outside(i0) for i0 in range(a, b - n + 1)]
            k = int(np.argmin(costs))
            cand = (costs[k], a + k)
            if best is None or cand[0] < best[0]:
                best = cand
    if best is None:
        raise RuntimeError(f"no {segment_s} s window ({mode})")
    if mode == "end":
        return int(best[2]), float(best[3])
    return int(best[1]), float(best[0])


def segment_from(lc, i0, n, max_gap_s, background_subtract):
    sl = slice(i0, i0 + n)
    frac = lc["frac"][sl]
    is_gap = frac < 1.0
    backrat = lc["backrat"] if background_subtract else 0.0
    bands, noise = {}, {}
    for name in ("soft", "hard"):
        src = lc[f"src_{name}"][sl].astype(float)
        bkg = lc[f"bkg_{name}"][sl].astype(float)
        net = src - backrat * bkg
        filled, _, _, long_gaps = base.fill_short_gaps(net, is_gap, max_gap_s, lc["dt"])
        if long_gaps:
            raise RuntimeError(long_gaps)
        bands[name] = filled
        good = ~is_gap
        var = src + (backrat ** 2) * bkg
        noise[name] = float(var[good].sum() / max(good.sum(), 1) * var.size)
    return bands, noise


def unbinned(segments, noises, dt):
    n = segments[0]["soft"].size
    freq = np.fft.rfftfreq(n, dt)
    c_acc = ps_acc = ph_acc = None
    for seg in segments:
        s = np.fft.rfft(seg["soft"] - np.mean(seg["soft"]))
        h = np.fft.rfft(seg["hard"] - np.mean(seg["hard"]))
        c = np.conj(h) * s
        ps = s.real ** 2 + s.imag ** 2
        ph = h.real ** 2 + h.imag ** 2
        c_acc = c if c_acc is None else c_acc + c
        ps_acc = ps if ps_acc is None else ps_acc + ps
        ph_acc = ph if ph_acc is None else ph_acc + ph
    m = len(segments)
    # Drop DC and the Nyquist bin, as the lag stage does before binning.
    sl = slice(1, -1)
    return {
        "freq": freq[sl],
        "cross": c_acc[sl] / m,
        "power_soft": ps_acc[sl] / m,
        "power_hard": ph_acc[sl] / m,
        "noise_soft": float(np.mean([x["soft"] for x in noises])),
        "noise_hard": float(np.mean([x["hard"] for x in noises])),
        "n_segments": m,
        "dt": dt,
        "n_time": n,
    }


def rebin_one(spec, lo, hi):
    f = spec["freq"]
    sel = (f >= lo) & (f < hi)
    nf = int(sel.sum())
    if nf == 0:
        return None
    m = spec["n_segments"]
    k = m * nf
    cb = np.mean(spec["cross"][sel])
    sb = float(np.mean(spec["power_soft"][sel]))
    hb = float(np.mean(spec["power_hard"][sel]))
    fm = float(np.mean(f[sel]))
    g2 = float(np.abs(cb) ** 2 / (sb * hb))
    if 0 < g2 < 1:
        dphi = math.sqrt((1.0 - g2) / (2.0 * g2 * k))
    elif g2 >= 1:
        dphi = 0.0
    else:
        dphi = float("inf")
    phi = float(np.angle(cb))
    with np.errstate(all="ignore"):
        gi, _ = intrinsic_coherence(
            np.array([cb]), np.array([sb]), np.array([hb]),
            spec["noise_soft"], spec["noise_hard"], k, return_uncertainty=True,
        )
    gi = float(gi[0])
    reliable = bool(np.isfinite(gi) and k >= 30 and math.isfinite(dphi))
    return {
        "f_lo_hz": float(lo),
        "f_hi_hz": float(hi),
        "f_mean_hz": fm,
        "n_freq": nf,
        "K": int(k),
        "lag_s": phi / (2 * math.pi * fm),
        "lag_err_s": dphi / (2 * math.pi * fm),
        "coherence_raw": g2,
        "coherence_intrinsic": gi if np.isfinite(gi) else None,
        "reliable": reliable,
    }


def load_points(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for row in rows:
        out.append({k: (float(row[k]) if k not in ("point", "series", "marker", "note") else row[k])
                    for k in row})
        out[-1]["point"] = int(row["point"])
    return out


def axis_range_s():
    doc = json.loads((REPO / "results/compare/digitised/ai-grok-4.7-2026-11-20/digitisation.json").read_text())
    lo, hi = doc["y_axis"]["plotted_range"]
    return float(hi) - float(lo), doc


def combine(ai, ay, floor):
    """Amendment 2: F09's values are the vector reading. δ still uses both readings."""
    if len(ai) != len(ay):
        raise RuntimeError(f"different numbers of points: {len(ai)} and {len(ay)}")
    rows = []
    for a, b in zip(ai, ay):
        dlag = abs(a["lag_s"] - b["lag_s"])
        s_ai = 0.5 * (a["lag_top_s"] - a["lag_bottom_s"])
        s_ay = 0.5 * (b["lag_top_s"] - b["lag_bottom_s"])
        s_ref = 0.5 * (s_ai + s_ay)
        dex = abs(math.log10(a["f_hz"] / b["f_hz"]))
        rows.append({
            "point": a["point"],
            "f_hz": a["f_hz"],
            "lag_s": a["lag_s"],
            "lag_top_s": a["lag_top_s"],
            "lag_bottom_s": a["lag_bottom_s"],
            "f_left_hz": a["f_left_hz"],
            "f_right_hz": a["f_right_hz"],
            "S_s": s_ai,
            "upper_s": a["lag_top_s"] - a["lag_s"],
            "lower_s": a["lag_s"] - a["lag_bottom_s"],
            "delta_s": max(0.5 * dlag, floor),
            "half_diff_s": 0.5 * dlag,
            "dex": dex,
            "agree": bool(dlag < 0.25 * s_ref and dex < 0.02),
            "ay_f_hz": b["f_hz"],
            "ay_lag_s": b["lag_s"],
            "ay_S_s": s_ay,
            "ay_f_left_hz": b["f_left_hz"],
            "ay_f_right_hz": b["f_right_hz"],
            "ay_lag_top_s": b["lag_top_s"],
            "ay_lag_bottom_s": b["lag_bottom_s"],
            "mean_f_hz": 0.5 * (a["f_hz"] + b["f_hz"]),
            "mean_lag_s": 0.5 * (a["lag_s"] + b["lag_s"]),
            "mean_S_s": 0.5 * (s_ai + s_ay),
            "mean_f_left_hz": 0.5 * (a["f_left_hz"] + b["f_left_hz"]),
            "mean_f_right_hz": 0.5 * (a["f_right_hz"] + b["f_right_hz"]),
            "censored_top": bool(a["lag_top_s"] >= 199.5),
        })
    return rows


def sign_crossing(freqs, lags, reliable):
    """Positive-to-negative zero, log-linear, both bins reliable. As in lags.py."""
    found = []
    for i in range(len(lags) - 1):
        if lags[i] > 0 >= lags[i + 1] and reliable[i] and reliable[i + 1]:
            x0, x1 = math.log10(freqs[i]), math.log10(freqs[i + 1])
            frac = lags[i] / (lags[i] - lags[i + 1])
            found.append({"i": i, "j": i + 1, "f_hz": 10 ** (x0 + (x1 - x0) * frac)})
    return found


def weighted_mean(lags, errs):
    lags = np.asarray(lags, float)
    errs = np.asarray(errs, float)
    w = 1.0 / errs ** 2
    return float(np.sum(w * lags) / np.sum(w)), float(w.sum() ** -0.5), w


def median_log_width(edges_left, edges_right):
    widths = np.log10(np.asarray(edges_right) / np.asarray(edges_left))
    return float(np.median(widths))


def shift_edges(left, right, fraction, width):
    """Move every edge by `fraction` of the median log10 bin width."""
    def move(v):
        return 10 ** (np.log10(v) + fraction * width)
    return move(np.asarray(left, float)), move(np.asarray(right, float))


def evaluate(spec, f09, window_specs, label):
    left = np.array([r["f_left_hz"] for r in f09])
    right = np.array([r["f_right_hz"] for r in f09])
    width = median_log_width(left, right)
    baseline = [rebin_one(spec, lo, hi) for lo, hi in zip(left, right)]
    count = [bool(b and b["reliable"]) for b in baseline]

    def z_of(variant_rows):
        zs = []
        for i, (b, v) in enumerate(zip(baseline, variant_rows)):
            if not count[i] or v is None or not math.isfinite(v["lag_err_s"]) or v["lag_err_s"] <= 0:
                zs.append(None)
                continue
            zs.append((b["lag_s"] - v["lag_s"]) / v["lag_err_s"])
        used = [z for z in zs if z is not None]
        if not used:
            return {"z": zs, "rms": None, "max_abs": None}
        return {"z": zs, "rms": float(np.sqrt(np.mean(np.square(used)))), "max_abs": float(np.max(np.abs(used)))}

    variants = {}
    for frac in (-0.10, -0.05, 0.05, 0.10):
        sl, sr = shift_edges(left, right, frac, width)
        rows = [rebin_one(spec, lo, hi) for lo, hi in zip(sl, sr)]
        variants[f"edges_{frac:+.2f}"] = z_of(rows)
    for name, vspec in window_specs.items():
        rows = [rebin_one(vspec, lo, hi) for lo, hi in zip(left, right)]
        variants[name] = z_of(rows)
    rms_limit = max(v["rms"] for v in variants.values() if v["rms"] is not None)
    z_limit = max(v["max_abs"] for v in variants.values() if v["max_abs"] is not None)

    table = []
    for i, (src, b) in enumerate(zip(f09, baseline)):
        if b is None:
            table.append({"point": src["point"], "compared": False, "reason": "no Fourier frequencies"})
            continue
        d = b["lag_s"] - src["lag_s"]
        denom_f = math.sqrt(src["S_s"] ** 2 + src["delta_s"] ** 2)
        denom_c = math.sqrt(b["lag_err_s"] ** 2 + src["S_s"] ** 2 + src["delta_s"] ** 2)
        z_f = d / denom_f
        z_c = d / denom_c
        opposite = (b["lag_s"] * src["lag_s"] < 0
                    and abs(b["lag_s"]) > 2 * b["lag_err_s"]
                    and abs(src["lag_s"]) > 2 * src["S_s"])
        table.append({
            "point": src["point"],
            "compared": True,
            "counts": count[i],
            "f_hz": src["f_hz"],
            "f_lo_hz": b["f_lo_hz"],
            "f_hi_hz": b["f_hi_hz"],
            "f_mean_hz": b["f_mean_hz"],
            "n_freq": b["n_freq"],
            "K": b["K"],
            "lag_s": b["lag_s"],
            "lag_err_s": b["lag_err_s"],
            "f09_lag_s": src["lag_s"],
            "S_s": src["S_s"],
            "delta_s": src["delta_s"],
            "d_s": d,
            "z_F": z_f,
            "z_C": z_c,
            "rho": b["lag_err_s"] / src["S_s"],
            "reliable": b["reliable"],
            "opposite_signs_over_2sigma": bool(opposite),
            "upper_s": src["upper_s"],
            "lower_s": src["lower_s"],
        })

    counting = [r for r in table if r.get("counts")]
    zf = np.array([r["z_F"] for r in counting])
    zc = np.array([r["z_C"] for r in counting])
    chi = float(np.sum(zc ** 2))
    ndf = int(zc.size)
    ours_cross = sign_crossing(
        [r["f_mean_hz"] for r in table if r.get("compared")],
        [r["lag_s"] for r in table if r.get("compared")],
        [r["reliable"] for r in table if r.get("compared")],
    )
    # Map the crossing index back onto point numbers. `sign_crossing` indexes
    # only the compared rows, which are all twelve when none is empty.
    compared_points = [r["point"] for r in table if r.get("compared")]
    for c in ours_cross:
        c["points"] = [compared_points[c["i"]], compared_points[c["j"]]]
    f09_cross = sign_crossing(
        [r["f_hz"] for r in f09],
        [r["lag_s"] for r in f09],
        [True] * len(f09),
    )
    for c in f09_cross:
        c["points"] = [f09[c["i"]]["point"], f09[c["j"]]["point"]]

    in_range = [r for r in counting if F_LO <= r["f_hz"] < F_HI]
    if in_range:
        m_ours, e_ours, _ = weighted_mean([r["lag_s"] for r in in_range], [r["lag_err_s"] for r in in_range])
        m_f09, e_f09, w = weighted_mean([r["f09_lag_s"] for r in in_range], [r["S_s"] for r in in_range])
        delta_m = float(np.sum(w * np.array([r["delta_s"] for r in in_range])) / np.sum(w))
        z_mean = (m_ours - m_f09) / math.sqrt(e_f09 ** 2 + delta_m ** 2)
    else:
        m_ours = e_ours = m_f09 = e_f09 = delta_m = z_mean = None

    def pair_distance(a, b):
        if len(a) != 1 or len(b) != 1:
            return None
        return abs(a[0]["points"][0] - b[0]["points"][0])

    dist = pair_distance(ours_cross, f09_cross)
    rms_zf = float(np.sqrt(np.mean(zf ** 2))) if zf.size else None
    max_zf = float(np.max(np.abs(zf))) if zf.size else None
    within = bool(rms_zf is not None and rms_zf <= rms_limit and max_zf <= z_limit)
    rho = np.array([r["rho"] for r in counting])
    median_rho = float(np.median(rho)) if rho.size else None
    bars = "similar" if median_rho is not None and 0.67 <= median_rho <= 1.5 else "differ"

    single = len(ours_cross) == 1 and len(f09_cross) == 1
    far_sign = bool(single and dist is not None and dist > 1)
    adjacent_or_same = bool(single and dist is not None and dist <= 1)
    opposite = any(r["opposite_signs_over_2sigma"] for r in counting)
    zmean_abs = abs(z_mean) if z_mean is not None else None

    if not single or z_mean is None or rms_limit is None:
        amended = "not covered by the plan"
        amended_reason = "sign change is not a single crossing, or a mean or the spread is missing"
    elif zmean_abs > 2 or opposite or far_sign:
        amended = "does not agree"
        amended_reason = "large mean difference, opposite signs, or a distant sign change"
    elif zmean_abs <= 1 and adjacent_or_same and within:
        amended = "agrees with F09 Fig. 3"
        amended_reason = "mean, sign change and spread all inside the amended limits"
    else:
        amended = "agrees, with differences"
        amended_reason = "between the two amended limits"
        if zmean_abs > 1:
            amended_reason += f"; |z_mean|={zmean_abs:.3f}"
        if not within:
            amended_reason += "; outside our own spread"

    if not single:
        original = "not covered by the plan"
    elif any(abs(z) > 2 for z in zf) or opposite or far_sign:
        original = "does not agree"
    elif all(abs(z) <= 1 for z in zf) and adjacent_or_same:
        original = "agrees with F09 Fig. 3"
    elif all(abs(z) <= 2 for z in zf) and any(1 < abs(z) <= 2 for z in zf):
        original = "agrees, with differences"
    else:
        original = "not covered by the plan"

    above = [r["point"] for r in counting if abs(r["z_F"]) > z_limit]
    return {
        "label": label,
        "n_compared": sum(1 for r in table if r.get("compared")),
        "n_count": len(counting),
        "table": table,
        "variants": {k: {"rms": v["rms"], "max_abs": v["max_abs"]} for k, v in variants.items()},
        "rms_limit": rms_limit,
        "abs_z_limit": z_limit,
        "rms_z_F": rms_zf,
        "max_abs_z_F": max_zf,
        "within_own_spread": within,
        "points_outside_abs_z_limit": above,
        "chi2": chi,
        "ndf": ndf,
        "chi2_probability": float(chi2.sf(chi, ndf)) if ndf else None,
        "ours_sign_change": ours_cross,
        "f09_sign_change": f09_cross,
        "sign_pair_distance": dist,
        "high_frequency_mean": {
            "points": [r["point"] for r in in_range],
            "ours_s": m_ours,
            "ours_err_s": e_ours,
            "f09_s": m_f09,
            "f09_err_s": e_f09,
            "delta_m_s": delta_m,
            "z_mean": z_mean,
        },
        "median_rho": median_rho,
        "error_bars": bars,
        "outcome_amendment_1": amended,
        "outcome_amendment_1_reason": amended_reason,
        "outcome_original": original,
        "median_log10_bin_width": width,
    }


def ratio_of_points(freqs):
    ratios = np.array(freqs[1:]) / np.array(freqs[:-1])
    logs = np.log(ratios)
    return {
        "geometric_mean_ratio": float(math.exp(np.mean(logs))),
        "scatter_of_ratio": float(np.std(ratios, ddof=1)),
        "ratios": ratios.tolist(),
    }


def check_against_committed(spec):
    """Geometric bins as in lags.py, compared with the committed rounded CSV."""
    f = spec["freq"]
    edges = [float(f[0]) * (1 - 1e-9)]
    while edges[-1] < float(f[-1]):
        edges.append(edges[-1] * 1.4)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        row = rebin_one(spec, lo, hi)
        if row:
            rows.append(row)
    committed = []
    lines = [ln for ln in open(REPO / "analysis/lags/lag_frequency.csv") if not ln.startswith("#")]
    for rec in csv.DictReader(lines):
        committed.append(rec)
    worst = 0.0
    worst_rel = None
    for mine, theirs in zip(rows, committed):
        if int(float(theirs["reliable"])) != 1:
            continue
        dl = abs(mine["lag_s"] - float(theirs["lag_s"]))
        if dl > worst:
            worst = dl
            worst_rel = (mine["f_mean_hz"], mine["lag_s"], float(theirs["lag_s"]))
    if len(rows) < 24:
        raise RuntimeError(f"rebuild produced {len(rows)} bins, expected at least 24")
    if worst > 0.05:
        raise RuntimeError(f"rebuild disagrees with the committed reliable lags by {worst} s at {worst_rel}")
    return {"n_bins": len(rows), "max_abs_reliable_lag_difference_vs_rounded_csv_s": worst,
            "worst_reliable": worst_rel}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (REPO / "params.yaml").open() as fh:
        params = yaml.safe_load(fh)
    files = {
        ("0511580101", "PNS001"): REPO / "reduction/raw/0511580101/P0511580101PNS001PIEVLI0000.FTZ",
        ("0511580201", "PNS001"): REPO / "reduction/raw/0511580201/P0511580201PNS001PIEVLI0000.FTZ",
        ("0511580301", "PNU002"): REPO / "reduction/raw/0511580301/P0511580301PNU002PIEVLI0000.FTZ",
        ("0511580401", "PNU002"): REPO / "reduction/raw/0511580401/P0511580401PNU002PIEVLI0000.FTZ",
    }
    max_gap = float(params["lags"]["max_gap_fill_s"])
    dt = float(params["lightcurves"]["dt_s"])
    subtract = bool(params["lags"]["background_subtract"])
    lcs = []
    for exp in params["exposures"]:
        if not exp["include"]:
            continue
        key = (exp["obsid"], exp["expo"])
        info, lc = base.process_exposure(files[key], params["filter"], params["lightcurves"])
        lcs.append({"key": key, "lc": lc, "info": info})
        print(f"loaded {key[0]} {key[1]}", flush=True)

    def spectrum_for(segment_s, mode):
        segments, noises, placed = [], [], []
        for item in lcs:
            i0, cost = place_window(item["lc"], segment_s, max_gap, mode)
            bands, noise = segment_from(item["lc"], i0, int(round(segment_s / dt)), max_gap, subtract)
            segments.append(bands)
            noises.append(noise)
            placed.append({"obsid": item["key"][0], "expo": item["key"][1],
                           "start_offset_s": i0 * dt, "time_outside_flare_s": cost})
        spec = unbinned(segments, noises, dt)
        spec["placement"] = placed
        return spec

    baseline = spectrum_for(100000.0, "min_flare")
    check = check_against_committed(baseline)
    print("rebuild check", check, flush=True)

    window_specs = {}
    for length in (95000.0, 90000.0, 80000.0):
        window_specs[f"window_{length/1000:.0f}ks"] = spectrum_for(length, "min_flare")
    window_specs["window_100ks_at_end"] = spectrum_for(100000.0, "end")

    ai = load_points(REPO / "results/compare/digitised/ai-grok-4.7-2026-11-20/points.csv")
    ay = load_points(REPO / "results/compare/digitised/ay/points.csv")
    span, axis_doc = axis_range_s()
    floor = 0.005 * span
    primary = combine(ai, ay, floor)

    def as_f09(rows, prefix):
        """prefix '' is the vector reading; 'ay_' and 'mean_' are the sensitivities."""
        if prefix == "":
            return rows
        out = []
        for r in rows:
            out.append({
                **r,
                "f_hz": r[f"{prefix}f_hz"],
                "lag_s": r[f"{prefix}lag_s"],
                "S_s": r[f"{prefix}S_s"],
                "f_left_hz": r[f"{prefix}f_left_hz"],
                "f_right_hz": r[f"{prefix}f_right_hz"],
                "upper_s": r[f"{prefix}lag_top_s"] - r[f"{prefix}lag_s"] if prefix != "mean_" else None,
                "lower_s": r[f"{prefix}lag_s"] - r[f"{prefix}lag_bottom_s"] if prefix != "mean_" else None,
            })
            if prefix == "mean_":
                top = 0.5 * (r["lag_top_s"] + r["ay_lag_top_s"])
                bot = 0.5 * (r["lag_bottom_s"] + r["ay_lag_bottom_s"])
                out[-1]["upper_s"] = top - out[-1]["lag_s"]
                out[-1]["lower_s"] = out[-1]["lag_s"] - bot
        return out

    primary_eval = evaluate(baseline, primary, window_specs, "vector reading (Amendment 2)")
    ay_eval = evaluate(baseline, as_f09(primary, "ay_"), window_specs, "AY digitisation alone")
    mean_rows = as_f09(primary, "mean_")
    # mean_S was stored; as_f09 reads mean_S_s. Good.
    mean_eval = evaluate(baseline, mean_rows, window_specs, "mean of both readings")

    def slim(ev):
        return {k: v for k, v in ev.items() if k != "table"}

    result = {
        "source": "rebuilt from the raw event lists with FRACEXP < 1 interpolated; checked against the committed lag table",
        "rebuild_check": check,
        "baseline_placement_s": baseline["placement"],
        "window_variant_placement_s": {k: v["placement"] for k, v in window_specs.items()},
        "digitisation_floor_s": floor,
        "plotted_lag_axis_range_s": span,
        "agreement": [{"point": r["point"], "agree": r["agree"], "half_diff_s": r["half_diff_s"],
                       "dex": r["dex"], "delta_s": r["delta_s"], "censored_top": r["censored_top"]}
                      for r in primary],
        "f09_frequency_ratio": ratio_of_points([r["f_hz"] for r in primary]),
        "primary": slim(primary_eval),
        "sensitivity_ay": slim(ay_eval),
        "sensitivity_mean": slim(mean_eval),
        "quarter_bin_edge_shift": (
            "not applied: Amendment 2 takes the bin edges from horizontal bars, and the plan "
            "applies the quarter-bin shift only when the edges come from midpoints"
        ),
        "outcomes_changed_by_sensitivity": {
            "ay_amendment_1": ay_eval["outcome_amendment_1"] != primary_eval["outcome_amendment_1"],
            "mean_amendment_1": mean_eval["outcome_amendment_1"] != primary_eval["outcome_amendment_1"],
            "ay_original": ay_eval["outcome_original"] != primary_eval["outcome_original"],
            "mean_original": mean_eval["outcome_original"] != primary_eval["outcome_original"],
        },
    }
    with (OUT / "comparison_own.json").open("w") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    with (OUT / "comparison_own.csv").open("w", newline="\n") as fh:
        cols = ["point", "counts", "f_hz", "f_mean_hz", "lag_s", "lag_err_s", "f09_lag_s", "S_s",
                "delta_s", "d_s", "z_F", "z_C", "rho", "reliable"]
        fh.write(",".join(cols) + "\n")
        for row in primary_eval["table"]:
            if not row.get("compared"):
                fh.write(f"{row['point']},no\n")
                continue
            fh.write(",".join(str(row[c]) for c in cols) + "\n")
    print("Amendment 1:", primary_eval["outcome_amendment_1"])
    print("original:", primary_eval["outcome_original"])
    print("z_mean", primary_eval["high_frequency_mean"]["z_mean"])
    print("rms z_F", primary_eval["rms_z_F"], "limit", primary_eval["rms_limit"])
    print("max |z_F|", primary_eval["max_abs_z_F"], "limit", primary_eval["abs_z_limit"])
    print("outside", primary_eval["points_outside_abs_z_limit"])
    print("sign ours", primary_eval["ours_sign_change"])
    print("sign f09", primary_eval["f09_sign_change"])


if __name__ == "__main__":
    main()

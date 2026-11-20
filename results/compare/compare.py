#!/usr/bin/env python3
"""Stage 5 (compare): R1 against the digitised points of Fabian et al. 2009 (F09), Fig. 3.

Implements results/compare/PLAN.md, which was fixed (commit 13438ec) before any point of Fig. 3 was digitised, and
its Amendment 1 (2026-11-20), made before the comparison was run. This code was written and tested on made-up input
(test_compare.py) before the explainer had seen any digitised value. The two digitisations had already been committed
on their own branches (PLAN.md, "What actually happened"). Choices the plan leaves to the code are listed in
results/compare/EXPLAIN.md.

Steps:
  1. Self-checks: re-binning our cross spectrum on the lags stage's own bins, bin by bin, must reproduce
     analysis/lags/lag_frequency.csv. Our values on any bin come from lags.bin_spectra, the function that made R1.
     Rebuilding the baseline segments from the light curves must reproduce unbinned_cross_spectrum.npz exactly.
  2. Read the two digitisations (results/compare/digitised/<id>/points.csv and digitisation.json), match their
     points, run the agreement check and combine them (mean of the two readings; half the difference, with a floor
     of 0.5% of the plotted lag-axis range, is the digitisation uncertainty delta).            (A-18)
     Amendment 2 (A-20): F09's values are taken from the primary digitisation (PRIMARY_DIGITISATION, the vector
     reading), with delta still from both readings; the mean of both is reported as a sensitivity variant.
  3. F09's frequency bins: ends of horizontal error bars if drawn, otherwise geometric midpoints between
     consecutive points. Only the frequencies of F09's points are used for this.                  (A-15)
  4. Our lag on each F09 bin; per bin d = ours - F09, z_F = d / sqrt(S^2 + delta^2) (main statistic),
     z_C = d / sqrt(sigma^2 + S^2 + delta^2), rho = sigma / S. F09 error bars taken as 1 sigma.  (A-16)
  5. Our own spread (Amendment 1, A-19): the same z for reference variants of our own analysis (bin edges moved by
     +-0.05 and +-0.10 of a bin; 95, 90 and 80 ks windows; the 100 ks window at the end of each orbit's usable
     stretch), each against our baseline on F09's bins.
  6. The outcome under the amended criteria (high-frequency weighted mean, sign change, opposite signs, and the
     points against our own spread), the outcome under the original criteria (13438ec), and both for the
     sensitivity variants.

SIGN CONVENTION (as R1 and F09 Fig. 3): lag > 0 means the hard band (1-4 keV) lags the soft band (0.3-1 keV).

Usage (from the repository root):
    python results/compare/compare.py                                 # the real digitisations
    python results/compare/compare.py --digitised DIR --out DIR --label "MADE-UP TEST INPUT"
    python results/compare/compare.py --calibrate                     # our own spread on our own bins (no F09)
"""
from __future__ import annotations

import argparse
import csv
import functools
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from astropy.io import fits
from astropy.table import Table
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "lags"))
import lags  # noqa: E402  the lags stage; lags.bin_spectra made R1

import matplotlib.pyplot as plt  # noqa: E402  (lags has already selected the Agg backend)

NPZ = ROOT / "analysis/lags/output/unbinned_cross_spectrum.npz"
CSV_R1 = ROOT / "analysis/lags/lag_frequency.csv"
LCDIR = ROOT / "analysis/lightcurves/output"
PLAN = "results/compare/PLAN.md (commit 13438ec, with Amendments 1 and 2 of 2026-11-20)"

# Numbers fixed in PLAN.md. Do not change them without a new commit of the plan and a LOG entry.
AGREE_DLAG_FRAC_OF_S = 0.25      # agreement check: lags differ by less than 0.25 S
AGREE_DLOGF_DEX = 0.02           # agreement check: frequencies differ by less than 0.02 dex
DELTA_FLOOR_FRAC = 0.005         # digitisation uncertainty floor: 0.5% of the plotted lag-axis range (A-18)
Z_AGREE, Z_DIFFER = 1.0, 2.0     # ORIGINAL plan (13438ec): outcome thresholds on |z_F|; still computed and reported
OPPOSITE_SIGN_NSIGMA = 2.0       # opposite signs count only if each lag is more than 2 sigma from zero
RHO_SIMILAR = (0.67, 1.5)        # error bars "similar" if the median sigma/S is in this range
HF_RANGE_HZ = (7e-4, 5e-3)       # weighted-mean range (A-14)
EDGE_SHIFT_FRAC = 0.25           # sensitivity: edges shifted by +-1/4 bin width (midpoint edges only)
SINGLE_BIN_FACTOR = 1e9          # makes lags.bin_spectra put all the frequencies it is given into one bin
# Amendment 1 (2026-11-20, before the comparison was run)
Z_MEAN_AGREE, Z_MEAN_DIFFER = 1.0, 2.0          # outcome thresholds on |z_mean| (high-frequency weighted mean)
REF_EDGE_SHIFTS = (-0.10, -0.05, 0.05, 0.10)    # reference variants: all edges moved by this fraction of a bin (A-19)
REF_WINDOWS_S = (95000, 90000, 80000)           # reference variants: one window of this length per orbit (A-19)
CAL_EDGE_SHIFTS = (-0.25, 0.25)                 # calibration only (reported, not in the reference spread)
CAL_CUTS = (2, 3, 4)                            # calibration only: the 100 ks windows cut into this many segments
# Amendment 2 (2026-11-20, after the digitisations were received, before the comparison was run; A-20)
PRIMARY_DIGITISATION = "ai-grok-4.7-2026-11-20"  # F09's values come from this reading (vector extraction); delta from both

POINT_COLUMNS = ["point", "series", "f_hz", "lag_s", "lag_top_s", "lag_bottom_s", "f_left_hz", "f_right_hz",
                 "marker", "note"]


# --------------------------------------------------------------------------- helpers
def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def num(s) -> float:
    s = (s or "").strip()
    return float(s) if s else math.nan


def finite(x) -> bool:
    return x is not None and np.isfinite(x)


def clean(o):
    """JSON-safe copy: NaN and inf become null, numpy scalars become Python numbers."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    return o


def read_r1_csv():
    lines = [l for l in CSV_R1.read_text().splitlines() if not l.startswith("#")]
    return list(csv.DictReader(lines))


# --------------------------------------------------------------------------- our spectrum
def load_r1():
    """Unbinned cross spectrum of the baseline (Nyquist frequency dropped, as in lags.bin_spectra), and the
    Poisson noise levels, which lags.py writes to lag_frequency.csv (6 significant figures)."""
    d = np.load(NPZ)
    f, C, PS, PH = d["freq"][:-1], d["cross"][:-1], d["power_soft"][:-1], d["power_hard"][:-1]
    rows = read_r1_csv()
    return {"f": f, "C": C, "PS": PS, "PH": PH, "M": int(d["n_segments"]),
            "noise_soft": float(rows[0]["noise_soft"]), "noise_hard": float(rows[0]["noise_hard"]), "rows": rows}


def per_bin(r1, lo, hi):
    """Our binned values for Fourier frequencies lo <= f < hi, computed by lags.bin_spectra (the R1 code)."""
    k = (r1["f"] >= lo) & (r1["f"] < hi)
    if not k.any():
        return None
    rows = lags.bin_spectra(r1["f"][k], r1["C"][k], r1["PS"][k], r1["PH"][k], r1["M"], r1["noise_soft"],
                            r1["noise_hard"], SINGLE_BIN_FACTOR, nyq_exclude=False)
    assert len(rows) == 1
    row = dict(rows[0])
    row["f_lo_hz"], row["f_hi_hz"] = lo, hi
    return row


def self_check(r1):
    """Re-bin on the lags stage's own edges with per_bin; compare with lags.bin_spectra and with the CSV."""
    factor = yaml.safe_load(open(ROOT / "params.yaml"))["lags"]["freq_bin_factor"]
    f = r1["f"]
    edges = [f[0] * (1 - 1e-9)]
    while edges[-1] < f[-1]:
        edges.append(edges[-1] * factor)
    mine = [b for b in (per_bin(r1, lo, hi) for lo, hi in zip(edges[:-1], edges[1:])) if b is not None]
    ref = lags.bin_spectra(f, r1["C"], r1["PS"], r1["PH"], r1["M"], r1["noise_soft"], r1["noise_hard"], factor,
                           nyq_exclude=False)
    cols = ["f_mean_hz", "K", "lag_s", "lag_err_s", "coh_raw", "coh_intrinsic", "reliable"]
    same_as_function = len(mine) == len(ref) and all(
        np.allclose([a[c] for a in mine], [b[c] for b in ref], rtol=1e-12, atol=0, equal_nan=True) for c in cols)
    csvrows = r1["rows"]
    tol = {"coh_intrinsic": (1e-4, 1e-6)}
    same_as_csv = len(mine) == len(csvrows)
    worst = {}
    if same_as_csv:
        for c in cols:
            a = np.array([m[c] for m in mine], float)
            b = np.array([float(r[c]) for r in csvrows])
            rt, at = tol.get(c, (2e-5, 0.0))
            ok = np.allclose(a, b, rtol=rt, atol=at, equal_nan=True)
            both = np.isfinite(a) & np.isfinite(b)
            worst[c] = float(np.max(np.abs(a[both] - b[both]) / np.maximum(np.abs(b[both]), 1e-300))) if both.any() else 0.0
            same_as_csv &= bool(ok)
    return {"freq_bin_factor": factor, "n_bins": len(mine), "same_as_lags_bin_spectra": bool(same_as_function),
            "same_as_lag_frequency_csv": bool(same_as_csv), "max_relative_difference_from_csv": worst,
            "passed": bool(same_as_function and same_as_csv)}


# --------------------------------------------------------------------------- other segmentations (Amendment 1)
def usable_mask(tab, A, dt):
    """Bins that are fully exposed or inside a gap short enough to interpolate: as in lags.choose_segments."""
    full = np.asarray(tab["FRACEXP"]) >= 1.0
    usable = full.copy()
    maxgap = int(np.floor(A["max_gap_fill_s"] / dt))
    for a, b in lags.runs(~full):
        if (b - a) <= maxgap and a > 0 and b < full.size:
            usable[a:b] = True
    return usable


def light_curve_files():
    P = yaml.safe_load(open(ROOT / "params.yaml"))
    return [LCDIR / f"{e['obsid']}_{e['expo']}_lc.fits" for e in P["exposures"] if e["include"]]


@functools.lru_cache(maxsize=None)
def segmented_spectrum(segment_s=None, placement="lags", cut=1):
    """Unbinned cross spectrum of the same light curves with another segmentation, built with the lags stage's own
    functions and following lags.main step by step. The defaults (segment length from params.yaml, the window that
    lags.choose_segments picks, no cut) give the baseline, which segmentation_check compares with the lags output.
    placement="end": the window is moved to the end of the usable stretch that holds the window lags would pick.
    cut=k: each window is cut into k equal segments. Returns a dict like load_r1 (Nyquist frequency dropped)."""
    P = yaml.safe_load(open(ROOT / "params.yaml"))
    L, A = P["lightcurves"], dict(P["lags"])
    if A["timing_gti"] != "orbit":
        raise SystemExit("the reference variants (A-19) are defined for lags.timing_gti: orbit (A-09)")
    if segment_s is not None:
        A["segment_s"] = segment_s
    dt = float(L["dt_s"])
    n = int(round(A["segment_s"] / dt))
    soft, hard, noise = [], [], {"SOFT": 0.0, "HARD": 0.0}
    for path in light_curve_files():
        with fits.open(path) as h:
            tab = Table.read(h["LIGHTCURVE"])
            r = float(h["LIGHTCURVE"].header["BACKRAT"])
        segs, _ = lags.choose_segments(tab, L, A, dt)
        if placement == "end" and segs:
            (i0, _), = segs
            a, b = next((a, b) for a, b in lags.runs(usable_mask(tab, A, dt)) if a <= i0 < b)
            segs = [(b - n, b)]
        if cut > 1:
            m = n // cut
            segs = [(i0 + j * m, i0 + (j + 1) * m) for i0, _ in segs for j in range(cut)]
        full = np.asarray(tab["FRACEXP"]) >= 1.0
        for i0, i1 in segs:
            g = full[i0:i1]
            for band, store in (("SOFT", soft), ("HARD", hard)):
                src = np.asarray(tab[f"SRC_{band}"][i0:i1], float)
                bkg = np.asarray(tab[f"BKG_{band}"][i0:i1], float)
                net = src - r * bkg if A["background_subtract"] else src
                var = src + (r ** 2 * bkg if A["background_subtract"] else 0.0)
                store.append(lags.fill_gaps(net, g) if not g.all() else net)
                noise[band] += var[g].sum() / g.sum() * g.size
    if not soft:
        raise SystemExit(f"no segments for segment_s={segment_s}, placement={placement}, cut={cut}")
    f, C, PS, PH, M = lags.averaged_spectra(soft, hard, dt)
    return {"f": f[:-1], "C": C[:-1], "PS": PS[:-1], "PH": PH[:-1], "M": M,
            "noise_soft": noise["SOFT"] / M, "noise_hard": noise["HARD"] / M}


def segmentation_check(r1):
    """The baseline rebuilt by segmented_spectrum must be the lags stage's cross spectrum, exactly."""
    sp = segmented_spectrum()
    same = sp["M"] == r1["M"] and sp["f"].size == r1["f"].size and all(
        np.allclose(sp[k], r1[k], rtol=1e-12, atol=0) for k in ("f", "C", "PS", "PH"))
    noise_ok = all(math.isclose(sp[k], r1[k], rel_tol=1e-5) for k in ("noise_soft", "noise_hard"))
    return {"same_as_unbinned_cross_spectrum": bool(same), "noise_levels_match_csv": bool(noise_ok),
            "passed": bool(same and noise_ok)}


# --------------------------------------------------------------------------- digitisations
def load_digitisation(d: Path):
    pts_path, meta_path = d / "points.csv", d / "digitisation.json"
    rows = list(csv.DictReader(pts_path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        raise SystemExit(f"{pts_path}: no points")
    missing = [c for c in POINT_COLUMNS if c not in rows[0]]
    if missing:
        raise SystemExit(f"{pts_path}: missing columns {missing}")
    series = sorted({r["series"].strip() for r in rows})
    if len(series) != 1:
        raise SystemExit(f"{pts_path}: more than one series {series}. PLAN.md does not say which to compare; "
                         "stop and decide in a new commit of the plan.")
    pts = []
    for r in rows:
        p = {"point": int(r["point"]), "f_hz": num(r["f_hz"]), "lag_s": num(r["lag_s"]),
             "lag_top_s": num(r["lag_top_s"]), "lag_bottom_s": num(r["lag_bottom_s"]),
             "f_left_hz": num(r["f_left_hz"]), "f_right_hz": num(r["f_right_hz"]),
             "marker": r["marker"].strip(), "note": r["note"].strip()}
        if not (finite(p["f_hz"]) and p["f_hz"] > 0 and finite(p["lag_s"])):
            raise SystemExit(f"{pts_path}: point {p['point']} has no valid frequency or lag")
        pts.append(p)
    pts.sort(key=lambda p: p["f_hz"])
    if np.any(np.diff([p["f_hz"] for p in pts]) <= 0):
        raise SystemExit(f"{pts_path}: two points have the same frequency")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    yr = meta["y_axis"]["plotted_range"]
    return {"id": d.name, "points": pts, "meta": meta, "series": series[0], "y_range_s": abs(yr[1] - yr[0]),
            "md5": {"points.csv": md5(pts_path), "digitisation.json": md5(meta_path)}}


def has_hbar(p) -> bool:
    return finite(p["f_left_hz"]) and finite(p["f_right_hz"])


def match_points(a, b):
    """Mutual nearest neighbours in log frequency, closer than half the smallest point spacing of either."""
    la = np.log10([p["f_hz"] for p in a])
    lb = np.log10([p["f_hz"] for p in b])
    spacing = min([np.min(np.diff(x)) for x in (la, lb) if x.size > 1] or [np.inf])
    pairs = []
    for i, x in enumerate(la):
        j = int(np.argmin(np.abs(lb - x)))
        if int(np.argmin(np.abs(la - lb[j]))) == i and abs(lb[j] - x) < spacing / 2:
            pairs.append((i, j))
    ua = [i for i in range(len(a)) if i not in {p[0] for p in pairs}]
    ub = [j for j in range(len(b)) if j not in {p[1] for p in pairs}]
    return pairs, ua, ub


def error_bar(top, bottom, lag):
    if finite(top) and finite(bottom):
        return (top - bottom) / 2, (top - lag) - (lag - bottom)
    return math.nan, math.nan


def combine(da, db):
    """Combine two digitisations as PLAN.md step 4 says. Returns points (matched ones usable for the comparison;
    unmatched ones only supply a frequency for the bin edges) and the agreement-check report."""
    a, b = da["points"], db["points"]
    pairs, ua, ub = match_points(a, b)
    floor = DELTA_FLOOR_FRAC * (da["y_range_s"] + db["y_range_s"]) / 2
    out, checks = [], []
    for i, j in pairs:
        pa, pb = a[i], b[j]
        if has_hbar(pa) != has_hbar(pb):
            raise SystemExit(f"points {da['id']}:{pa['point']} and {db['id']}:{pb['point']}: only one digitiser "
                             "recorded a horizontal error bar. Both should look again (PLAN.md step 4).")
        c = {k: (pa[k] + pb[k]) / 2 for k in ("f_hz", "lag_s", "lag_top_s", "lag_bottom_s", "f_left_hz", "f_right_hz")}
        S, asym = error_bar(c["lag_top_s"], c["lag_bottom_s"], c["lag_s"])
        dlag = pa["lag_s"] - pb["lag_s"]
        dlogf = math.log10(pa["f_hz"]) - math.log10(pb["f_hz"])
        half = lambda k: abs(pa[k] - pb[k]) / 2 if finite(pa[k]) and finite(pb[k]) else math.nan
        lag_ok = bool(abs(dlag) < AGREE_DLAG_FRAC_OF_S * S) if finite(S) else None
        f_ok = bool(abs(dlogf) < AGREE_DLOGF_DEX)
        out.append({"points": {da["id"]: pa["point"], db["id"]: pb["point"]}, "usable": True, **c,
                    "S": S, "asym_s": asym, "delta_s": max(abs(dlag) / 2, floor),
                    "delta_top_s": max(half("lag_top_s"), floor) if finite(half("lag_top_s")) else math.nan,
                    "delta_bottom_s": max(half("lag_bottom_s"), floor) if finite(half("lag_bottom_s")) else math.nan,
                    "hbar": has_hbar(pa)})
        checks.append({"points": {da["id"]: pa["point"], db["id"]: pb["point"]}, "f_hz": c["f_hz"],
                       "dlag_s": dlag, "dlag_over_S": dlag / S if finite(S) and S > 0 else None,
                       "dlogf_dex": dlogf, "lag_agrees": lag_ok, "f_agrees": f_ok,
                       "passes": bool(f_ok and lag_ok is not False)})
    for ids, pts, dd in ((ua, a, da), (ub, b, db)):
        for i in ids:
            p = pts[i]
            out.append({"points": {dd["id"]: p["point"]}, "usable": False, "f_hz": p["f_hz"], "lag_s": p["lag_s"],
                        "lag_top_s": p["lag_top_s"], "lag_bottom_s": p["lag_bottom_s"],
                        "f_left_hz": p["f_left_hz"], "f_right_hz": p["f_right_hz"], "S": math.nan,
                        "asym_s": math.nan, "delta_s": math.nan, "delta_top_s": math.nan,
                        "delta_bottom_s": math.nan, "hbar": has_hbar(p)})
    out.sort(key=lambda p: p["f_hz"])
    report = {"floor_s": floor, "n_matched": len(pairs),
              "unmatched": {da["id"]: [a[i]["point"] for i in ua], db["id"]: [b[j]["point"] for j in ub]},
              "n_failing": sum(not c["passes"] for c in checks), "points": checks}
    return out, report


def primary_points(dp, ds):
    """Amendment 2 (A-20): F09's values (frequency, lag, error-bar ends, horizontal-bar ends) from the primary
    digitisation dp; the digitisation uncertainty delta still from both readings, as in A-18 (half the difference,
    at least the floor). Only points found by both are compared; points found by one digitiser only are kept, not
    compared, so that their frequencies still supply bin edges (as in combine)."""
    a, b = dp["points"], ds["points"]
    pairs, ua, ub = match_points(a, b)
    floor = DELTA_FLOOR_FRAC * (dp["y_range_s"] + ds["y_range_s"]) / 2
    keys = ("f_hz", "lag_s", "lag_top_s", "lag_bottom_s", "f_left_hz", "f_right_hz")
    out = []
    for i, j in pairs:
        pa, pb = a[i], b[j]
        if has_hbar(pa) != has_hbar(pb):
            raise SystemExit(f"points {dp['id']}:{pa['point']} and {ds['id']}:{pb['point']}: only one digitiser "
                             "recorded a horizontal error bar. Both should look again (PLAN.md step 4).")
        S, asym = error_bar(pa["lag_top_s"], pa["lag_bottom_s"], pa["lag_s"])
        half = lambda k: abs(pa[k] - pb[k]) / 2 if finite(pa[k]) and finite(pb[k]) else math.nan
        out.append({"points": {dp["id"]: pa["point"], ds["id"]: pb["point"]}, "usable": True, **{k: pa[k] for k in keys},
                    "S": S, "asym_s": asym, "delta_s": max(half("lag_s"), floor),
                    "delta_top_s": max(half("lag_top_s"), floor) if finite(half("lag_top_s")) else math.nan,
                    "delta_bottom_s": max(half("lag_bottom_s"), floor) if finite(half("lag_bottom_s")) else math.nan,
                    "hbar": has_hbar(pa)})
    for ids, pts, dd in ((ua, a, dp), (ub, b, ds)):
        for i in ids:
            q = pts[i]
            out.append({"points": {dd["id"]: q["point"]}, "usable": False, **{k: q[k] for k in keys}, "S": math.nan,
                        "asym_s": math.nan, "delta_s": math.nan, "delta_top_s": math.nan, "delta_bottom_s": math.nan,
                        "hbar": has_hbar(q)})
    out.sort(key=lambda q: q["f_hz"])
    return out


def single(dd):
    """One digitisation on its own (sensitivity variant): delta is the floor only."""
    floor = DELTA_FLOOR_FRAC * dd["y_range_s"]
    out = []
    for p in dd["points"]:
        S, asym = error_bar(p["lag_top_s"], p["lag_bottom_s"], p["lag_s"])
        out.append({"points": {dd["id"]: p["point"]}, "usable": True,
                    **{k: p[k] for k in ("f_hz", "lag_s", "lag_top_s", "lag_bottom_s", "f_left_hz", "f_right_hz")},
                    "S": S, "asym_s": asym, "delta_s": floor, "delta_top_s": floor, "delta_bottom_s": floor,
                    "hbar": has_hbar(p)})
    return out


# --------------------------------------------------------------------------- F09 bins (A-15)
def f09_edges(points, shift=0.0):
    hb = [p["hbar"] for p in points]
    if all(hb):
        if shift:
            return None, "horizontal error bars (no edge shift applies)"
        return [(p["f_left_hz"], p["f_right_hz"]) for p in points], "horizontal error bars"
    if any(hb):
        raise SystemExit("some points have horizontal error bars and others do not; PLAN.md does not cover this")
    if len(points) < 2:
        raise SystemExit("fewer than two points: bin edges cannot be inferred")
    lf = np.log10([p["f_hz"] for p in points])
    mid = (lf[:-1] + lf[1:]) / 2
    lo = np.concatenate([[lf[0] - (lf[1] - lf[0]) / 2], mid])
    hi = np.concatenate([mid, [lf[-1] + (lf[-1] - lf[-2]) / 2]])
    if shift:
        w = float(np.median(hi - lo))
        lo, hi = lo + shift * w, hi + shift * w
    return list(zip(10 ** lo, 10 ** hi)), "geometric midpoints between points" + (f", shifted by {shift:+.2f} of the median bin width" if shift else "")


def shift_edges(edges, s):
    """All edges moved by s times the median bin width in log frequency (reference variants; any kind of edges)."""
    lo = np.log10([e[0] for e in edges])
    hi = np.log10([e[1] for e in edges])
    w = float(np.median(hi - lo))
    return list(zip(10 ** (lo + s * w), 10 ** (hi + s * w)))


def spacing_fit(points):
    """Side result for A-11: fit log10 f_i = a + i log10 r to the point frequencies."""
    lf = np.log10([p["f_hz"] for p in points])
    if lf.size < 3:
        return None
    i = np.arange(lf.size)
    slope, icpt = np.polyfit(i, lf, 1)
    resid = lf - (icpt + slope * i)
    return {"n_points": int(lf.size), "ratio": float(10 ** slope), "rms_scatter_dex": float(np.sqrt(np.mean(resid ** 2))),
            "max_abs_scatter_dex": float(np.max(np.abs(resid))), "consecutive_ratios": [float(x) for x in 10 ** np.diff(lf)],
            "note": "ratio of consecutive point frequencies; A-11 (lags.freq_bin_factor) is 1.4, the literal reading of Z10 is 2.4"}


# --------------------------------------------------------------------------- comparison
def compare_bins(r1, points, edges):
    bins = []
    for j, (p, (lo, hi)) in enumerate(zip(points, edges)):
        b = {"bin": j + 1, "f09_points": p["points"], "f_lo_hz": lo, "f_hi_hz": hi, "f09_f_hz": p["f_hz"],
             "f09_lag_s": p["lag_s"], "f09_err_S_s": p["S"], "f09_err_asym_s": p["asym_s"],
             "f09_lag_top_s": p["lag_top_s"], "f09_lag_bottom_s": p["lag_bottom_s"], "delta_s": p["delta_s"],
             "delta_top_s": p["delta_top_s"], "delta_bottom_s": p["delta_bottom_s"]}
        ours = per_bin(r1, lo, hi)
        if ours is None:
            b["status"] = "no Fourier frequency of ours in this bin"
            bins.append(b)
            continue
        b.update({"n_freq": ours["n_freq"], "K": ours["K"], "ours_f_mean_hz": ours["f_mean_hz"],
                  "dlogf_ours_minus_f09_dex": math.log10(ours["f_mean_hz"] / p["f_hz"]),
                  "ours_lag_s": ours["lag_s"], "ours_lag_err_s": ours["lag_err_s"],
                  "ours_coh_raw": ours["coh_raw"], "ours_coh_intrinsic": ours["coh_intrinsic"],
                  "ours_reliable": ours["reliable"]})
        if not p["usable"]:
            b["status"] = "found by one digitiser only"
        elif not finite(p["S"]):
            b["status"] = "no complete error bar"
        else:
            tau, sig, T, S, dl = ours["lag_s"], ours["lag_err_s"], p["lag_s"], p["S"], p["delta_s"]
            d = tau - T
            b.update({"d_s": d, "z_F": d / math.sqrt(S ** 2 + dl ** 2),
                      "z_C": d / math.sqrt(sig ** 2 + S ** 2 + dl ** 2), "rho": sig / S if S > 0 else math.nan})
            b["status"] = "counts" if ours["reliable"] else "ours not reliable (A-13)"
        bins.append(b)
    return bins


def crossings(freqs, values, positions):
    """Positive-to-negative sign changes between consecutive entries (log-linear interpolation, as lags.py)."""
    out = []
    for a in range(len(values) - 1):
        if values[a] > 0 >= values[a + 1]:
            x0, x1 = math.log10(freqs[a]), math.log10(freqs[a + 1])
            fc = 10 ** (x0 + (x1 - x0) * values[a] / (values[a] - values[a + 1]))
            out.append({"f_hz": fc, "between_bins": [positions[a], positions[a + 1]], "pair_index": a})
    return out


def wmean(vals, errs):
    v, e = np.asarray(vals, float), np.asarray(errs, float)
    k = e > 0
    if not k.any():
        return None
    w = 1 / e[k] ** 2
    return {"n_bins": int(k.sum()), "weighted_mean_lag_s": float(np.sum(w * v[k]) / w.sum()), "error_s": float(w.sum() ** -0.5)}


def opposite_sign_bins(counting):
    return [b["bin"] for b in counting
            if np.sign(b["ours_lag_s"]) * np.sign(b["f09_lag_s"]) < 0
            and abs(b["ours_lag_s"]) > OPPOSITE_SIGN_NSIGMA * b["ours_lag_err_s"]
            and abs(b["f09_lag_s"]) > OPPOSITE_SIGN_NSIGMA * b["f09_err_S_s"]]


def classify(counting, sc, hfm, ptp):
    """Outcome under PLAN.md as amended (Amendment 1). `counting`: bins that count; `sc`: sign-change comparison
    (status 'same or adjacent', 'far' or 'undetermined'); `hfm`: high-frequency weighted means, with 'z_mean';
    `ptp`: the points against our own spread, with 'within_our_spread' (True, False or None)."""
    if not counting:
        return "not covered by the plan", ["no bin counts"]
    zm = hfm.get("z_mean") if hfm else None
    opposite = opposite_sign_bins(counting)
    reasons = []
    if zm is not None and abs(zm) > Z_MEAN_DIFFER:
        reasons.append(f"high-frequency weighted mean differs by |z_mean| = {abs(zm):.2f} > {Z_MEAN_DIFFER:g}")
    if opposite:
        reasons.append(f"opposite signs, each more than {OPPOSITE_SIGN_NSIGMA:g} sigma from zero, in bin(s) {opposite}")
    if sc["status"] == "far":
        reasons.append("sign change more than one bin away from F09's")
    if reasons:
        return "does not agree", reasons
    if zm is None:
        return "not covered by the plan", ["the high-frequency weighted mean could not be computed "
                                           f"(no bin that counts in {HF_RANGE_HZ[0]:g}-{HF_RANGE_HZ[1]:g} Hz)"]
    within = ptp.get("within_our_spread")
    if abs(zm) <= Z_MEAN_AGREE and sc["status"] == "same or adjacent" and within:
        return "agrees", [f"high-frequency weighted mean within {Z_MEAN_AGREE:g} (|z_mean| = {abs(zm):.2f}); sign change "
                          "in the same or an adjacent pair of bins; the points are no further from ours than our own "
                          f"reference variants are (rms z_F {ptp['rms_z_F']:.2f} <= {ptp['rms_limit']:.2f}, "
                          f"max |z_F| {ptp['max_abs_z_F']:.2f} <= {ptp['abs_z_limit']:.2f})"]
    diffs = []
    if abs(zm) > Z_MEAN_AGREE:
        diffs.append(f"high-frequency weighted mean differs by |z_mean| = {abs(zm):.2f}, between {Z_MEAN_AGREE:g} "
                     f"and {Z_MEAN_DIFFER:g}")
    if within is False:
        diffs.append(f"the points differ from ours by more than our own reference variants do: rms z_F "
                     f"{ptp['rms_z_F']:.2f} (limit {ptp['rms_limit']:.2f}), max |z_F| {ptp['max_abs_z_F']:.2f} "
                     f"(limit {ptp['abs_z_limit']:.2f}); bin(s) beyond the limit: {ptp['bins_beyond_abs_z_limit']}")
    unknown = ([f"the sign-change criterion could not be applied ({sc['detail']})"] if sc["status"] == "undetermined" else []) + (
        ["our own spread could not be computed"] if within is None else [])
    if diffs:
        return "agrees, with differences", diffs + unknown
    return "not covered by the plan", ["no criterion for a difference is met, but " + "; ".join(unknown)]


def classify_original(counting, sc):
    """Outcome under the ORIGINAL PLAN.md (13438ec), still computed and reported. `counting`: bins that count (dicts
    with z_F, ours/f09 lags and errors); `sc`: sign-change comparison with key 'status' in {'same or adjacent', 'far',
    'undetermined'}."""
    if not counting:
        return "not covered by the plan", ["no bin counts"]
    reasons = []
    az = [abs(b["z_F"]) for b in counting]
    over2 = [b["bin"] for b in counting if abs(b["z_F"]) > Z_DIFFER]
    between = [b["bin"] for b in counting if Z_AGREE < abs(b["z_F"]) <= Z_DIFFER]
    opposite = opposite_sign_bins(counting)
    if over2:
        reasons.append(f"|z_F| > {Z_DIFFER:g} in bin(s) {over2}")
    if opposite:
        reasons.append(f"opposite signs, each more than {OPPOSITE_SIGN_NSIGMA:g} sigma from zero, in bin(s) {opposite}")
    if sc["status"] == "far":
        reasons.append("sign change more than one bin away from F09's")
    if reasons:
        return "does not agree", reasons
    if max(az) <= Z_AGREE and sc["status"] == "same or adjacent":
        return "agrees", [f"|z_F| <= {Z_AGREE:g} in all {len(counting)} bins that count; sign change in the same or an adjacent pair of bins"]
    if between:
        return "agrees, with differences", [f"every |z_F| <= {Z_DIFFER:g}; between {Z_AGREE:g} and {Z_DIFFER:g} in bin(s) {between}"] + (
            [f"sign change: {sc['status']}"] if sc["status"] != "same or adjacent" else [])
    return "not covered by the plan", [f"every |z_F| <= {Z_AGREE:g}, but the sign-change criterion could not be applied ({sc['detail']})"]


def reference_specs():
    """The reference variants of Amendment 1 (A-19): name -> (kind, value)."""
    v = {f"edges moved {s:+.2f} bin": ("edges", s) for s in REF_EDGE_SHIFTS}
    v.update({f"one {s / 1e3:.0f} ks window per orbit": ("spectrum", (s, "lags", 1)) for s in REF_WINDOWS_S})
    v["100 ks window at the end of the usable stretch"] = ("spectrum", (None, "end", 1))
    return v


def calibration_only_specs():
    """Larger variants, reported in the calibration only: not part of the reference spread."""
    v = {f"edges moved {s:+.2f} bin": ("edges", s) for s in CAL_EDGE_SHIFTS}
    v.update({f"100 ks windows cut into {k} segments": ("spectrum", (None, "lags", k)) for k in CAL_CUTS})
    return v


def variant_rows(r1, spec, edges):
    kind, val = spec
    if kind == "edges":
        return [per_bin(r1, lo, hi) for lo, hi in shift_edges(edges, val)]
    sp = segmented_spectrum(*val)
    return [per_bin(sp, lo, hi) for lo, hi in edges]


def spread(r1, edges, counting, ref_key, specs):
    """Our own spread: for each variant, z = (ours - variant) / variant's error in each bin that counts (the analogue
    of z_F, with no digitisation term), and the variant's high-frequency weighted mean and sign change.
    `counting`: bins that count, numbered 1.. along `edges`, with ours_lag_s and ours_lag_err_s; `ref_key`: the
    frequency used to pick the high-frequency bins (F09's point frequency in the comparison)."""
    out = {}
    for name, spec in specs.items():
        rows = variant_rows(r1, spec, edges)
        have = [(b, rows[b["bin"] - 1]) for b in counting if rows[b["bin"] - 1] is not None]
        z = {b["bin"]: (b["ours_lag_s"] - v["lag_s"]) / v["lag_err_s"] for b, v in have}
        za = np.array(list(z.values()))
        hf = [(b, v) for b, v in have if HF_RANGE_HZ[0] <= b[ref_key] < HF_RANGE_HZ[1]]
        mo = wmean([b["ours_lag_s"] for b, _ in hf], [b["ours_lag_err_s"] for b, _ in hf])
        mv = wmean([v["lag_s"] for _, v in hf], [v["lag_err_s"] for _, v in hf])
        cv = crossings([v["f_mean_hz"] for _, v in have], [v["lag_s"] for _, v in have], [b["bin"] for b, _ in have])
        out[name] = {"n_bins": int(za.size), "z": z,
                     "rms_z": float(np.sqrt(np.mean(za ** 2))) if za.size else None,
                     "max_abs_z": float(np.max(np.abs(za))) if za.size else None,
                     "high_frequency_mean": mv,
                     "z_mean": (mo["weighted_mean_lag_s"] - mv["weighted_mean_lag_s"]) / mv["error_s"] if mo and mv else None,
                     "sign_changes": [{"f_hz": c["f_hz"], "between_bins": c["between_bins"]} for c in cv]}
    ok = {k: v for k, v in out.items() if v["n_bins"]}
    lim = lambda key: max(ok.items(), key=lambda kv: kv[1][key]) if ok else (None, {key: None})
    (rms_by, rms_v), (abs_by, abs_v) = lim("rms_z"), lim("max_abs_z")
    return {"variants": out, "rms_limit": rms_v["rms_z"], "rms_limit_from": rms_by,
            "abs_z_limit": abs_v["max_abs_z"], "abs_z_limit_from": abs_by}


def evaluate(r1, points, shift=0.0):
    edges, edge_source = f09_edges(points, shift)
    if edges is None:
        return None
    bins = compare_bins(r1, points, edges)
    counting = [b for b in bins if b["status"] == "counts"]
    pos = [b["bin"] for b in counting]
    co = crossings([b["ours_f_mean_hz"] for b in counting], [b["ours_lag_s"] for b in counting], pos)
    cf = crossings([b["f09_f_hz"] for b in counting], [b["f09_lag_s"] for b in counting], pos)
    if len(co) == 1 and len(cf) == 1:
        dist = abs(co[0]["pair_index"] - cf[0]["pair_index"])
        sc = {"status": "same or adjacent" if dist <= 1 else "far", "pair_distance": dist,
              "detail": f"ours between bins {co[0]['between_bins']}, F09 between bins {cf[0]['between_bins']}"}
    else:
        sc = {"status": "undetermined", "detail": f"{len(co)} sign change(s) in ours and {len(cf)} in F09's points "
                                                    "among the bins that count; the plan assumes one each"}
    sc.update({"ours": co, "f09": cf})
    rho = [b["rho"] for b in counting if finite(b.get("rho"))]
    med_rho = float(np.median(rho)) if rho else math.nan
    hf = [b for b in counting if HF_RANGE_HZ[0] <= b["f09_f_hz"] < HF_RANGE_HZ[1]]
    mo = wmean([b["ours_lag_s"] for b in hf], [b["ours_lag_err_s"] for b in hf])
    mf = wmean([b["f09_lag_s"] for b in hf], [b["f09_err_S_s"] for b in hf])
    hfm = {"f_range_hz": list(HF_RANGE_HZ), "ours": mo, "f09": mf}
    if mo and mf:
        w = np.array([b["f09_err_S_s"] ** -2.0 for b in hf if b["f09_err_S_s"] > 0])
        dl = np.array([b["delta_s"] for b in hf if b["f09_err_S_s"] > 0])
        hfm["difference_s"] = mo["weighted_mean_lag_s"] - mf["weighted_mean_lag_s"]
        hfm["difference_over_f09_error"] = hfm["difference_s"] / mf["error_s"]
        # digitisation uncertainty of F09's mean, taken as fully correlated between points (the larger choice)
        hfm["delta_s"] = float(np.sum(w * dl) / np.sum(w))
        hfm["z_mean"] = hfm["difference_s"] / math.sqrt(mf["error_s"] ** 2 + hfm["delta_s"] ** 2)
    sp = spread(r1, edges, counting, "f09_f_hz", reference_specs())
    zf = np.array([b["z_F"] for b in counting])
    ptp = {"rms_z_F": float(np.sqrt(np.mean(zf ** 2))) if zf.size else None,
           "max_abs_z_F": float(np.max(np.abs(zf))) if zf.size else None,
           "rms_limit": sp["rms_limit"], "abs_z_limit": sp["abs_z_limit"]}
    if zf.size and sp["abs_z_limit"] is not None:
        ptp["within_our_spread"] = bool(ptp["rms_z_F"] <= sp["rms_limit"] and ptp["max_abs_z_F"] <= sp["abs_z_limit"])
        ptp["bins_beyond_abs_z_limit"] = [b["bin"] for b in counting if abs(b["z_F"]) > sp["abs_z_limit"]]
    else:
        ptp["within_our_spread"] = None
    outcome, reasons = classify(counting, sc, hfm, ptp)
    outcome0, reasons0 = classify_original(counting, sc)
    zc = [b["z_C"] for b in counting]
    return {"edge_source": edge_source, "bins": bins, "n_bins": len(bins),
            "n_bins_by_status": {s: sum(b["status"] == s for b in bins) for s in sorted({b["status"] for b in bins})},
            "outcome": outcome, "reasons": reasons,
            "outcome_original_plan": outcome0, "reasons_original_plan": reasons0,
            "sign_change": sc, "point_by_point": ptp, "reference_spread": sp,
            "max_abs_z_F": max([abs(b["z_F"]) for b in counting], default=None),
            "chi2_combined": {"chi2": float(np.sum(np.square(zc))), "dof": len(zc),
                              "p_value": float(stats.chi2.sf(np.sum(np.square(zc)), len(zc))) if zc else None,
                              "note": "too lenient: the two analyses share photons (PLAN.md); for completeness only"},
            "error_bars": {"median_rho": med_rho,
                           "verdict": ("similar" if RHO_SIMILAR[0] <= med_rho <= RHO_SIMILAR[1] else "differ") if rho else None},
            "high_frequency_mean": hfm}


# --------------------------------------------------------------------------- outputs
def write_csv(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: (f"{r[c]:.6g}" if isinstance(r.get(c), float) else
                            json.dumps(r[c]) if isinstance(r.get(c), dict) else r.get(c, "")) for c in cols})


def plot(path, ev, title, f09_label):
    bins = ev["bins"]
    fig, ax = plt.subplots(2, 1, figsize=(8, 7.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    have = [b for b in bins if "ours_lag_s" in b]
    for rel, kw in ((1, dict(fmt="o", color="k", ms=5, lw=1, label="ours, re-binned onto F09's bins (reliable)")),
                    (0, dict(fmt="o", color="0.6", mfc="none", ms=5, lw=0.8, label="ours (not reliable, A-13)"))):
        s = [b for b in have if b["ours_reliable"] == rel]
        if s:
            fm = np.array([b["ours_f_mean_hz"] for b in s])
            xe = np.array([[m - b["f_lo_hz"] for m, b in zip(fm, s)], [b["f_hi_hz"] - m for m, b in zip(fm, s)]])
            ax[0].errorbar(fm, [b["ours_lag_s"] for b in s], yerr=[b["ours_lag_err_s"] for b in s], xerr=xe, **kw)
    F = np.array([b["f09_f_hz"] for b in bins])
    T = np.array([b["f09_lag_s"] for b in bins])
    top = np.array([b["f09_lag_top_s"] for b in bins], float)
    bot = np.array([b["f09_lag_bottom_s"] for b in bins], float)
    yerr = np.array([np.where(np.isfinite(bot), T - bot, 0), np.where(np.isfinite(top), top - T, 0)])
    ax[0].errorbar(F, T, yerr=yerr, fmt="s", color="tab:orange", ms=5, lw=1, label=f09_label)
    cnt = [b for b in bins if b["status"] == "counts"]
    vals = [v for b in cnt for v in (b["ours_lag_s"] - b["ours_lag_err_s"], b["ours_lag_s"] + b["ours_lag_err_s"],
                                     b["f09_lag_s"] - b["f09_err_S_s"], b["f09_lag_s"] + b["f09_err_S_s"])]
    if vals:
        lo_y, hi_y = min(vals), max(vals)
        pad = 0.15 * (hi_y - lo_y)
        ax[0].set_ylim(lo_y - pad, hi_y + pad)
    ax[0].axhline(0, color="grey", lw=0.8)
    ax[0].set_xscale("log")
    ax[0].set_ylabel("lag (s)   [> 0: hard lags soft]")
    ax[0].legend(fontsize=8, loc="best")
    ax[0].set_title(title, fontsize=9)
    zb = [b for b in bins if "z_F" in b]
    lim = ev["point_by_point"]["abs_z_limit"]
    if lim is not None:
        ax[1].axhspan(-lim, lim, color="0.88", lw=0, label=f"our own spread: largest |z| of the reference variants ({lim:.2f})")
    for zl in (Z_AGREE, Z_DIFFER):
        for sg in (-1, 1):
            ax[1].axhline(sg * zl, color="0.5", lw=0.6, ls=":")
    ax[1].axhline(0, color="grey", lw=0.8)
    fpos = {b["bin"]: b["f09_f_hz"] for b in bins}
    vx = [fpos[j] for v in ev["reference_spread"]["variants"].values() for j in v["z"]]
    vy = [z for v in ev["reference_spread"]["variants"].values() for z in v["z"].values()]
    if vx:
        ax[1].plot(vx, vy, ls="none", marker=".", ms=3, color="0.55", label="reference variants of our own analysis")
    who = "made-up points" if f09_label.startswith("made-up") else "F09 points"
    for counts, kw in ((True, dict(marker="o", color="k", ls="none", ms=5, label=f"{who}, bins that count")),
                       (False, dict(marker="o", color="0.6", mfc="none", ls="none", ms=5, label=f"{who}, other bins"))):
        s = [b for b in zb if (b["status"] == "counts") == counts]
        if s:
            ax[1].plot([b["f09_f_hz"] for b in s], [b["z_F"] for b in s], **kw)
    ax[1].set_ylabel("z_F = (ours − F09) / F09 error")
    ax[1].set_xlabel("frequency (Hz)   [dotted: ±1, ±2, original plan]")
    ax[1].legend(fontsize=7, loc="best")
    zmax = max([abs(b["z_F"]) for b in zb] + [abs(y) for y in vy] + [2.5])
    ax[1].set_ylim(-min(zmax * 1.15, 10), min(zmax * 1.15, 10))
    hfm = ev["high_frequency_mean"]
    hft = (f"; high-frequency mean: ours {hfm['ours']['weighted_mean_lag_s']:.1f} ± {hfm['ours']['error_s']:.1f} s, "
           f"F09 {hfm['f09']['weighted_mean_lag_s']:.1f} ± {hfm['f09']['error_s']:.1f} s, z_mean {hfm['z_mean']:+.2f}"
           if hfm.get("z_mean") is not None else "")
    fig.text(0.01, 0.022, f"Outcome (PLAN.md with Amendment 1): {ev['outcome']}{hft}", fontsize=7.5)
    fig.text(0.01, 0.004, f"Outcome under the original plan (13438ec): {ev['outcome_original_plan']}", fontsize=7.5)
    plt.tight_layout(rect=(0, 0.04, 1, 1))
    plt.savefig(path, dpi=110)
    plt.close(fig)


BIN_COLUMNS = ["bin", "status", "f_lo_hz", "f_hi_hz", "f09_f_hz", "f09_lag_s", "f09_err_S_s", "f09_err_asym_s",
               "delta_s", "n_freq", "K", "ours_f_mean_hz", "dlogf_ours_minus_f09_dex", "ours_lag_s", "ours_lag_err_s",
               "ours_reliable", "ours_coh_intrinsic", "d_s", "z_F", "z_C", "rho", "f09_points"]
POINT_OUT_COLUMNS = ["f_hz", "lag_s", "lag_top_s", "lag_bottom_s", "f_left_hz", "f_right_hz", "S", "asym_s",
                     "delta_s", "delta_top_s", "delta_bottom_s", "usable", "points"]


def run(dirs, out: Path, label: str | None = None, primary: str | None = None):
    """primary: the id of the digitisation that gives F09's values (Amendment 2); None for the mean of both."""
    dirs = [Path(d) for d in dirs]
    if len(dirs) != 2:
        raise SystemExit(f"PLAN.md needs exactly two digitisations; found {len(dirs)}: {[d.name for d in dirs]}")
    out.mkdir(parents=True, exist_ok=True)
    r1 = load_r1()
    chk = self_check(r1)
    if not chk["passed"]:
        raise SystemExit(f"self-check FAILED: re-binning does not reproduce R1: {chk}")
    chk["segmentation"] = segmentation_check(r1)
    if not chk["segmentation"]["passed"]:
        raise SystemExit(f"self-check FAILED: rebuilding the segments does not reproduce the lags stage: {chk}")
    da, db = (load_digitisation(d) for d in dirs)
    combined, agreement = combine(da, db)
    variants = {}
    if primary is None:
        points, used = combined, f"mean of {da['id']} and {db['id']}"
    else:
        ids = [da["id"], db["id"]]
        if primary not in ids:
            raise SystemExit(f"primary digitisation {primary!r} not found among {ids} (PLAN.md Amendment 2)")
        dp, ds = (da, db) if da["id"] == primary else (db, da)
        points, used = primary_points(dp, ds), f"{primary} (primary, Amendment 2); delta from both readings"
    base = evaluate(r1, points)
    if primary is not None:
        variants["mean of both digitisations (plan before Amendment 2)"] = evaluate(r1, combined)
    for s in (-EDGE_SHIFT_FRAC, EDGE_SHIFT_FRAC):
        ev = evaluate(r1, points, s)
        if ev is not None:
            variants[f"edges shifted {s:+.2f} bin"] = ev
    for dd in (da, db):
        variants[f"{dd['id']} alone"] = evaluate(r1, single(dd))
    usable = [p for p in points if p["usable"]]
    summary = {
        "label": label, "plan": PLAN,
        "sign_convention": "lag > 0: hard (1-4 keV) lags soft (0.3-1 keV); lag < 0: soft lags hard",
        "inputs": {"unbinned_cross_spectrum.npz": md5(NPZ), "lag_frequency.csv": md5(CSV_R1),
                   **{p.name: md5(p) for p in light_curve_files()},
                   **{f"{dd['id']}/{k}": v for dd in (da, db) for k, v in dd["md5"].items()}},
        "digitisers": {dd["id"]: {k: dd["meta"].get(k) for k in ("digitiser", "source", "method", "tool",
                                                                 "had_seen_retrace_result", "had_seen_other_digitisation",
                                                                 "error_bars_stated_as", "nature_version_checked")}
                       for dd in (da, db)},
        "self_check": chk,
        "f09_values_from": used, "primary_digitisation": primary,
        "digitisation_agreement": agreement,
        "bin_spacing_A11": spacing_fit(points),
        "outcome": base["outcome"], "reasons": base["reasons"],
        "outcome_original_plan": base["outcome_original_plan"], "reasons_original_plan": base["reasons_original_plan"],
        "baseline": base,
        "sensitivity": {k: {"outcome": v["outcome"], "reasons": v["reasons"],
                            "outcome_original_plan": v["outcome_original_plan"], "max_abs_z_F": v["max_abs_z_F"],
                            "point_by_point": v["point_by_point"], "high_frequency_mean": v["high_frequency_mean"],
                            "edge_source": v["edge_source"], "n_bins_by_status": v["n_bins_by_status"]}
                        for k, v in variants.items()},
        "n_points": {"matched": len(usable), "unmatched": len(points) - len(usable)},
    }
    write_csv(out / "digitised_combined.csv", combined, POINT_OUT_COLUMNS)
    if primary is not None:
        write_csv(out / "digitised_primary.csv", points, POINT_OUT_COLUMNS)
    write_csv(out / "comparison.csv", base["bins"], BIN_COLUMNS)
    json.dump(clean(summary), open(out / "comparison.json", "w"), indent=2)
    title = label or f"R1 vs F09 Fig. 3, digitised: {used}; bins from {base['edge_source']}"
    f09_label = ("made-up test input (NOT F09)" if label else
                 f"F09 Fig. 3, digitised ({primary or 'mean of both'}; error bars as plotted)")
    plot(out / "comparison.png", base, title, f09_label)
    return summary


def calibrate(path: Path):
    """Our own spread on our own baseline bins (lags.freq_bin_factor), over the bins where our lag is reliable.
    Uses no F09 value. It shows how far the reference variants (A-19) and the larger
    calibration-only variants move single bins and the summary numbers."""
    r1 = load_r1()
    chk = self_check(r1)
    chk["segmentation"] = segmentation_check(r1)
    if not (chk["passed"] and chk["segmentation"]["passed"]):
        raise SystemExit(f"self-check FAILED: {chk}")
    factor = chk["freq_bin_factor"]
    f = r1["f"]
    edges = [f[0] * (1 - 1e-9)]
    while edges[-1] < f[-1]:
        edges.append(edges[-1] * factor)
    pairs = list(zip(edges[:-1], edges[1:]))
    rows = [per_bin(r1, lo, hi) for lo, hi in pairs]
    counting = [{"bin": j + 1, "ours_lag_s": b["lag_s"], "ours_lag_err_s": b["lag_err_s"], "ours_f_mean_hz": b["f_mean_hz"]}
                for j, b in enumerate(rows) if b is not None and b["reliable"]]
    ref = spread(r1, pairs, counting, "ours_f_mean_hz", reference_specs())
    extra = spread(r1, pairs, counting, "ours_f_mean_hz", calibration_only_specs())
    co = crossings([b["ours_f_mean_hz"] for b in counting], [b["ours_lag_s"] for b in counting],
                   [b["bin"] for b in counting])
    hf = [b for b in counting if HF_RANGE_HZ[0] <= b["ours_f_mean_hz"] < HF_RANGE_HZ[1]]
    allv = {**ref["variants"], **extra["variants"]}
    out = {
        "what": "Our own spread on our own baseline bins (PLAN.md Amendment 1, A-19). For each "
                "variant of our analysis: z = (baseline - variant) / variant error in each reliable bin, and the shift "
                "of the high-frequency weighted mean in units of the variant's error (z_mean). No F09 value is used.",
        "plan": PLAN,
        "inputs": {"unbinned_cross_spectrum.npz": md5(NPZ), "lag_frequency.csv": md5(CSV_R1),
                   **{p.name: md5(p) for p in light_curve_files()}},
        "self_check": chk,
        "bins": {"freq_bin_factor": factor, "n_reliable": len(counting),
                 "reliable": [{"bin": b["bin"], "f_lo_hz": pairs[b["bin"] - 1][0], "f_hi_hz": pairs[b["bin"] - 1][1],
                               "f_mean_hz": b["ours_f_mean_hz"], "lag_s": b["ours_lag_s"], "lag_err_s": b["ours_lag_err_s"]}
                              for b in counting]},
        "baseline": {"high_frequency_mean": wmean([b["ours_lag_s"] for b in hf], [b["ours_lag_err_s"] for b in hf]),
                     "sign_changes": [{"f_hz": c["f_hz"], "between_bins": c["between_bins"]} for c in co]},
        "reference_spread": {k: ref[k] for k in ("rms_limit", "rms_limit_from", "abs_z_limit", "abs_z_limit_from")},
        "calibration_only_spread": {k: extra[k] for k in ("rms_limit", "rms_limit_from", "abs_z_limit", "abs_z_limit_from")},
        "largest_abs_z_mean": {"reference": max(abs(v["z_mean"]) for v in ref["variants"].values()),
                               "all": max(abs(v["z_mean"]) for v in allv.values())},
        "sign_change_range_hz": [min(c["f_hz"] for v in allv.values() for c in v["sign_changes"]),
                                 max(c["f_hz"] for v in allv.values() for c in v["sign_changes"])],
        "variants": {"reference": ref["variants"], "calibration_only": extra["variants"]},
    }
    json.dump(clean(out), open(path, "w"), indent=2)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--digitised", default=str(ROOT / "results/compare/digitised"),
                    help="folder holding one sub-folder per digitisation")
    ap.add_argument("--out", default=str(ROOT / "results/compare"), help="output folder")
    ap.add_argument("--label", default=None, help="label for test runs (shown in the figure and the JSON)")
    ap.add_argument("--primary", default=PRIMARY_DIGITISATION,
                    help="id of the digitisation that gives F09's values (Amendment 2); 'none' for the mean of both")
    ap.add_argument("--calibrate", action="store_true",
                    help="write results/compare/calibration.json (our own spread on our own bins) and stop")
    a = ap.parse_args(argv)
    if a.calibrate:
        c = calibrate(ROOT / "results/compare/calibration.json")
        print(json.dumps(clean({k: c[k] for k in ("reference_spread", "calibration_only_spread", "largest_abs_z_mean",
                                                   "sign_change_range_hz")}), indent=2))
        for grp, vs in c["variants"].items():
            for name, v in vs.items():
                print(f"{grp:>16} | {name:<48} rms {v['rms_z']:.2f}  max {v['max_abs_z']:.2f}  z_mean {v['z_mean']:+.2f}  "
                      f"sign change {[round(x['f_hz'], 7) for x in v['sign_changes']]}")
        return
    base = Path(a.digitised)
    dirs = sorted(d for d in base.iterdir() if (d / "points.csv").exists()) if base.is_dir() else []
    s = run(dirs, Path(a.out), a.label, primary=None if a.primary == "none" else a.primary)
    print(json.dumps(clean({k: s[k] for k in ("outcome", "reasons", "outcome_original_plan", "self_check", "n_points")}), indent=2))
    print("sensitivity:", json.dumps(clean({k: v["outcome"] for k, v in s["sensitivity"].items()})))


if __name__ == "__main__":
    main()

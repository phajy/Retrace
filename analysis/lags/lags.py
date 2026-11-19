#!/usr/bin/env python3
"""Stage 4 (lags): averaged cross-spectrum, lag-frequency spectrum and coherence.

SIGN CONVENTION (same as Fabian et al. 2009 Fig. 3, Zoghbi et al. 2010, Kara et al. 2013):
    lag > 0  means the HARD band (1-4 keV) lags (changes after) the SOFT band (0.3-1 keV);
    lag < 0  means the SOFT band lags the hard band (the reported ~30 s reverberation lag).
Implemented as  lag(f) = arg< H*(f) S(f) > / (2 pi f)  with numpy's FFT sign convention
(H, S = FFTs of the hard and soft light curves), and checked every run with a synthetic
light-curve pair in which the hard band is delayed by a known amount (self-test below).

Method (choices not given in the paper are assumptions; see docs/assumptions.md):
  * background-subtracted light curves: net = SRC - BACKRAT * BKG              (A-08)
  * segments: `timing_gti: orbit` takes one window of `segment_s` per exposure,
    placed to minimise time outside the flare-screen GTIs; gaps up to
    `max_gap_fill_s` inside the window are filled by linear interpolation      (A-09, A-10)
    `timing_gti: flare_gti` instead uses only bins inside the flare GTIs (strict screen)
  * segment mean subtracted, rectangular window, numpy rfft
  * Fourier frequencies averaged over segments and over geometric frequency bins
    with edges f_{i+1} = freq_bin_factor * f_i                                (A-11)
  * raw coherence  g2 = |<C>|^2 / (<|S|^2> <|H|^2>)
  * phase error (Nowak et al. 1999 eq. 16; Bendat & Piersol):
        dphi = sqrt((1 - g2) / (2 g2 K)),  K = segments x Fourier frequencies in the bin
  * intrinsic (noise-corrected) coherence and its error: Vaughan & Nowak 1997 eq. 8,
    via stingray.fourier.intrinsic_coherence (bias term per Ingram 2019)
  * independent cross-check: Stingray AveragedCrossspectrum on the same segments must give
    the same lag at every Fourier frequency.

Usage:  python analysis/lags/lags.py   (normally via `dvc repro lags`)
"""
from __future__ import annotations

import csv
import json
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import yaml
from astropy.io import fits
from astropy.table import Table
from stingray.fourier import error_on_averaged_cross_spectrum, intrinsic_coherence

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LCDIR = ROOT / "analysis" / "lightcurves" / "output"
OUT = ROOT / "analysis" / "lags" / "output"
MIN_K = 30  # below this the analytic phase errors are unreliable (Stingray warns at n_ave < 30)


# --------------------------------------------------------------------------- segments
def runs(mask: np.ndarray):
    """(start, stop) index pairs of consecutive True runs."""
    m = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def fill_gaps(y: np.ndarray, good: np.ndarray) -> np.ndarray:
    """Linear interpolation of y over bins where good is False."""
    idx = np.arange(y.size)
    out = y.astype(float).copy()
    out[~good] = np.interp(idx[~good], idx[good], y[good])
    return out


def choose_segments(tab: Table, L: dict, A: dict, dt: float):
    """Return a list of (i0, i1) bin-index windows, each `n` bins long, plus notes."""
    n = int(round(A["segment_s"] / dt))
    fe = np.asarray(tab["FRACEXP"])
    inflare = np.asarray(tab["IN_FLAREGTI"])
    full = fe >= 1.0
    notes = {}
    if A["timing_gti"] == "orbit":
        # usable = fully exposed, or inside a gap short enough to be interpolated
        usable = full.copy()
        maxgap = int(np.floor(A["max_gap_fill_s"] / dt))
        for a, b in runs(~full):
            if (b - a) <= maxgap and a > 0 and b < full.size:
                usable[a:b] = True
        flaring = 1.0 - inflare  # fraction of each bin outside the flare-screen GTIs
        best = None
        for a, b in runs(usable):
            if b - a < n:
                continue
            c = np.concatenate([[0.0], np.cumsum(flaring[a:b])])
            cost = c[n:] - c[:-n]
            k = int(np.argmin(cost))  # earliest minimum
            if best is None or cost[k] < best[0]:
                best = (cost[k], a + k)
        if best is None:
            return [], {"reason": "no usable stretch as long as one segment"}
        i0 = best[1]
        notes = {"flaring_time_in_window_s": float(best[0] * dt),
                 "bins_interpolated": int(np.sum(~full[i0:i0 + n]))}
        return [(i0, i0 + n)], notes
    if A["timing_gti"] == "flare_gti":
        ok = full & (inflare >= 1.0)
        segs = []
        for a, b in runs(ok):
            k = a
            while k + n <= b:
                segs.append((k, k + n))
                k += n
        return segs, {"bins_interpolated": 0}
    raise ValueError(f"unknown timing_gti {A['timing_gti']!r}")


# --------------------------------------------------------------------------- spectra
def averaged_spectra(soft_segs, hard_segs, dt):
    """Segment-averaged C = conj(H) S, |S|^2, |H|^2 at the Fourier frequencies (numpy)."""
    n = len(soft_segs[0])
    f = np.fft.rfftfreq(n, dt)[1:]
    C = np.zeros(f.size, complex)
    PS = np.zeros(f.size)
    PH = np.zeros(f.size)
    for s, h in zip(soft_segs, hard_segs):
        S = np.fft.rfft(s - s.mean())[1:]
        H = np.fft.rfft(h - h.mean())[1:]
        C += np.conj(H) * S
        PS += np.abs(S) ** 2
        PH += np.abs(H) ** 2
    M = len(soft_segs)
    return f, C / M, PS / M, PH / M, M


def bin_spectra(f, C, PS, PH, M, noise_s, noise_h, factor, nyq_exclude=True):
    """Average in geometric frequency bins and compute lag, errors and coherence."""
    if nyq_exclude:  # drop the Nyquist frequency (real-valued FFT term)
        f, C, PS, PH = f[:-1], C[:-1], PS[:-1], PH[:-1]
    edges = [f[0] * (1 - 1e-9)]
    while edges[-1] < f[-1]:
        edges.append(edges[-1] * factor)
    edges = np.array(edges)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (f >= lo) & (f < hi)
        nf = int(k.sum())
        if nf == 0:
            continue
        K = M * nf
        fm = f[k].mean()
        Cb, Sb, Hb = C[k].mean(), PS[k].mean(), PH[k].mean()
        g2 = np.abs(Cb) ** 2 / (Sb * Hb)
        phi = np.angle(Cb)
        dphi = np.sqrt((1 - g2) / (2 * g2 * K)) if g2 < 1 else 0.0
        # intrinsic (noise-corrected) coherence and its error: Stingray's implementation of
        # Vaughan & Nowak 1997 eq. 8 (bias term per Ingram 2019); phase error as a cross-check
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gi, gi_err = intrinsic_coherence(np.array([Cb]), np.array([Sb]), np.array([Hb]),
                                             noise_s, noise_h, K, return_uncertainty=True)
            _, _, dphi_sr, _ = error_on_averaged_cross_spectrum(np.array([Cb]), np.array([Sb]),
                                                                np.array([Hb]), K, noise_s, noise_h)
        gi, gi_err, dphi_sr = float(gi[0]), float(gi_err[0]), float(dphi_sr[0])
        # reliable: intrinsic coherence defined (powers > 3 sigma above noise, Stingray's test)
        # and enough averaged estimates for the analytic error (K >= MIN_K)
        reliable = bool(np.isfinite(gi) and K >= MIN_K)
        rows.append({"f_lo_hz": lo, "f_hi_hz": hi, "f_mean_hz": fm, "n_freq": nf, "K": K,
                     "phase_rad": phi, "phase_err_rad": dphi, "phase_err_stingray_rad": dphi_sr,
                     "lag_s": phi / (2 * np.pi * fm), "lag_err_s": dphi / (2 * np.pi * fm),
                     "coh_raw": g2, "coh_intrinsic": gi, "coh_intrinsic_err": gi_err,
                     "power_soft": Sb, "power_hard": Hb, "noise_soft": noise_s, "noise_hard": noise_h,
                     "reliable": int(reliable)})
    return rows


def _synthetic_lag(dt, n, M, kind, seed, tau=30.0):
    """Synthetic pair with the HARD band delayed by tau; returns per-bin lags in 1e-4..3e-3 Hz."""
    rng = np.random.default_rng(seed)
    up = 10  # 1 s sub-samples per 10 s bin
    sub = dt / up
    soft_segs, hard_segs = [], []
    for _ in range(M):
        m = n * up + 2000
        w = rng.normal(size=m)
        if kind == "red":  # PSD ~ f^-2 above ~2.5e-4 Hz: integrate, then high-pass (running mean)
            x = np.cumsum(w)
            x -= np.convolve(x, np.ones(4000) / 4000, mode="same")
        else:
            x = w
        t = np.arange(m) * sub
        soft_segs.append(np.interp(t, t, x)[1000:1000 + n * up].reshape(n, up).mean(1))
        hard_segs.append(np.interp(t - tau, t, x)[1000:1000 + n * up].reshape(n, up).mean(1))
    f, C, PS, PH, Mm = averaged_spectra(soft_segs, hard_segs, dt)
    rows = bin_spectra(f, C, PS, PH, Mm, 0.0, 0.0, 1.4)
    return np.array([r["lag_s"] for r in rows if 1e-4 <= r["f_mean_hz"] <= 3e-3])


def self_test(dt, n, M):
    """Sign and units: white-noise pair, hard delayed by +30 s, must give +30 s (pass/fail).
    Red-noise leakage: same with a steep red-noise PSD; reported as a diagnostic (no pass/fail)."""
    tau = 30.0
    white = _synthetic_lag(dt, n, M, "white", 20090528, tau)
    red = _synthetic_lag(dt, n, 32, "red", 20090528, tau)
    return {"injected_lag_s": tau, "injected_sense": "hard delayed relative to soft (expect lag > 0)",
            "white_noise_median_lag_s_1e-4_to_3e-3_Hz": float(np.median(white)),
            "passed": bool(abs(np.median(white) - tau) < 1.0),
            "red_noise_leak_diagnostic": {
                "psd": "~f^-2 above ~2.5e-4 Hz, 32 segments, rectangular window",
                "median_lag_s_1e-4_to_3e-3_Hz": float(np.median(red)),
                "ratio_recovered_to_injected": float(np.median(red) / tau),
                "note": "red-noise leakage biases |lag| low for steep PSDs; see EXPLAIN.md"}}


def stingray_check(soft_segs, hard_segs, dt, f, C):
    """Compare our unbinned lag with Stingray's AveragedCrossspectrum on identical segments."""
    from stingray import AveragedCrossspectrum, Lightcurve
    n = len(soft_segs[0])
    tt = dt * (np.arange(n) + 0.5)

    def it(segs):
        for k, s in enumerate(segs):
            yield Lightcurve(tt + k * n * dt * 2, s, dt=dt, err=np.ones(n), err_dist="gauss",
                             skip_checks=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Stingray's time_lag is positive when lc1 lags lc2, so lc1 = HARD, lc2 = SOFT
        cs = AveragedCrossspectrum.from_lc_iterable(it(hard_segs), it(soft_segs), dt, n * dt,
                                                    norm="none", silent=True)
        lag_sr, _ = cs.time_lag()
    ours = np.angle(C) / (2 * np.pi * f)
    fm = min(len(cs.freq), len(f))
    same_freq = bool(np.allclose(cs.freq[:fm], f[:fm], rtol=1e-12))
    d = np.abs(np.asarray(lag_sr[:fm]) - ours[:fm])
    return {"stingray_n_segments": int(cs.m) if np.ndim(cs.m) == 0 else int(np.max(cs.m)),
            "same_frequency_grid": same_freq,
            "max_abs_lag_difference_s": float(np.nanmax(d)),
            "passed": bool(same_freq and np.nanmax(d) < 1e-6)}


# --------------------------------------------------------------------------- main
def main():
    P = yaml.safe_load(open(ROOT / "params.yaml"))
    L, A = P["lightcurves"], P["lags"]
    OUT.mkdir(parents=True, exist_ok=True)
    dt = float(L["dt_s"])
    soft_segs, hard_segs, seginfo = [], [], []
    noise_s = noise_h = 0.0
    for e in P["exposures"]:
        if not e["include"]:
            continue
        name = f"{e['obsid']}_{e['expo']}"
        with fits.open(LCDIR / f"{name}_lc.fits") as h:
            tab = Table.read(h["LIGHTCURVE"])
            r = float(h["LIGHTCURVE"].header["BACKRAT"])
        segs, notes = choose_segments(tab, L, A, dt)
        full = np.asarray(tab["FRACEXP"]) >= 1.0
        for i0, i1 in segs:
            g = full[i0:i1]
            out = {}
            for band in ("SOFT", "HARD"):
                src = np.asarray(tab[f"SRC_{band}"][i0:i1], float)
                bkg = np.asarray(tab[f"BKG_{band}"][i0:i1], float)
                net = src - r * bkg if A["background_subtract"] else src
                var = src + (r ** 2 * bkg if A["background_subtract"] else 0.0)
                out[band] = (fill_gaps(net, g) if not g.all() else net, var[g].sum() / g.sum() * g.size)
            soft_segs.append(out["SOFT"][0])
            hard_segs.append(out["HARD"][0])
            # Poisson noise level of |FFT|^2 for counts: sum of the per-bin variances
            noise_s += out["SOFT"][1]
            noise_h += out["HARD"][1]
            seginfo.append({"exposure": name, "tstart": float(tab["TIME"][i0] - dt / 2),
                            "tstop": float(tab["TIME"][i1 - 1] + dt / 2), "n_bins": int(i1 - i0),
                            "mean_soft_cps": float(out["SOFT"][0].mean() / dt),
                            "mean_hard_cps": float(out["HARD"][0].mean() / dt), **notes})
        if not segs:
            seginfo.append({"exposure": name, "segments": 0, **notes})
    good_segs = [s for s in seginfo if "n_bins" in s]
    M = len(good_segs)
    if M == 0:
        raise SystemExit("no segments selected")
    noise_s /= M
    noise_h /= M
    f, C, PS, PH, M = averaged_spectra(soft_segs, hard_segs, dt)
    rows = bin_spectra(f, C, PS, PH, M, noise_s, noise_h, A["freq_bin_factor"])

    test = self_test(dt, len(soft_segs[0]), max(M, 4))
    srchk = stingray_check(soft_segs, hard_segs, dt, f, C)

    # write the binned lag-frequency spectrum
    with open(ROOT / "analysis/lags/lag_frequency.csv", "w", newline="") as fh:
        fh.write("# Lag-frequency spectrum, 1H 0707-495, soft 0.3-1 keV vs hard 1-4 keV (EPIC-pn)\n")
        fh.write("# SIGN: lag_s > 0 means the HARD band lags the SOFT band; lag_s < 0 means SOFT lags HARD "
                 "(as in Fabian et al. 2009 Fig. 3)\n")
        fh.write("# produced by analysis/lags/lags.py; see analysis/lags/EXPLAIN.md\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for row in rows:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in row.items()})

    # summary numbers (facts; interpretation lives in the report)
    fm = np.array([r["f_mean_hz"] for r in rows])
    lag = np.array([r["lag_s"] for r in rows])
    err = np.array([r["lag_err_s"] for r in rows])
    rel = np.array([r["reliable"] for r in rows], bool)

    def wmean(lo, hi):
        k = (fm >= lo) & (fm < hi) & (err > 0) & rel
        if not k.any():
            return None
        wts = 1 / err[k] ** 2
        return {"f_range_hz": [lo, hi], "n_bins": int(k.sum()),
                "weighted_mean_lag_s": float(np.sum(wts * lag[k]) / wts.sum()),
                "error_s": float(wts.sum() ** -0.5)}

    crossings = []
    for i in range(len(rows) - 1):
        if lag[i] > 0 >= lag[i + 1] and rel[i] and rel[i + 1]:
            x0, x1 = np.log10(fm[i]), np.log10(fm[i + 1])
            crossings.append(float(10 ** (x0 + (x1 - x0) * lag[i] / (lag[i] - lag[i + 1]))))
    summary = {
        "sign_convention": "lag > 0: hard (1-4 keV) lags soft (0.3-1 keV); lag < 0: soft lags hard",
        "timing_gti": A["timing_gti"], "segment_s": A["segment_s"], "n_segments": M,
        "dt_s": dt, "pattern_max": L["pattern_max"], "background_subtract": A["background_subtract"],
        "freq_bin_factor": A["freq_bin_factor"],
        "segments": seginfo,
        "high_freq_mean_lag": {"7e-4_to_5e-3_Hz": wmean(7e-4, 5e-3), "7e-4_to_1e-2_Hz": wmean(7e-4, 1e-2)},
        "low_freq_mean_lag": {"1e-4_to_5e-4_Hz": wmean(1e-4, 5e-4)},
        "positive_to_negative_crossing_hz": crossings,
        "reliable_bins_f_range_hz": [float(fm[rel].min()), float(fm[rel].max())] if rel.any() else None,
        "most_negative_reliable_bin": ({"f_mean_hz": float(fm[rel][np.argmin(lag[rel])]),
                                        "lag_s": float(lag[rel].min()),
                                        "lag_err_s": float(err[rel][np.argmin(lag[rel])])}
                                       if rel.any() else None),
        "self_test_sign": test,
        "stingray_cross_check": srchk,
        "published_for_comparison_only": {
            "fabian2009_text": "soft band follows hard by about 30 s above ~0.6 mHz (Fig. 3 caption: 7e-4 Hz)"},
    }
    json.dump(summary, open(ROOT / "analysis/lags/summary.json", "w"), indent=2)

    # plot in the style of Fig. 3 (log frequency, linear lag) plus coherence
    fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    flo = np.array([r["f_lo_hz"] for r in rows])
    fhi = np.array([r["f_hi_hz"] for r in rows])
    xerr = [fm - flo, fhi - fm]
    xerr = np.array(xerr)
    ax[0].errorbar(fm[rel], lag[rel], yerr=err[rel], xerr=xerr[:, rel], fmt="o", ms=4, color="k", lw=1,
                   label=f"reliable (intrinsic coherence defined, K >= {MIN_K})")
    ax[0].errorbar(fm[~rel], lag[~rel], yerr=err[~rel], xerr=xerr[:, ~rel], fmt="o", ms=4, mfc="none",
                   color="0.6", lw=0.8, label="not reliable (noise-dominated or too few estimates)")
    lo_y, hi_y = -100, 300
    off = (lag < lo_y) | (lag > hi_y)
    for x0, y0 in zip(fm[off], lag[off]):
        ax[0].annotate(f"{y0:.0f}", (x0, np.clip(y0, lo_y + 10, hi_y - 10)), fontsize=7, color="0.4",
                       ha="center")
    ax[0].legend(fontsize=8, loc="upper right")
    ax[0].axhline(0, color="grey", lw=0.8)
    ax[0].set_xscale("log")
    ax[0].set_ylabel("lag (s)   [> 0: hard lags soft]")
    ax[0].set_ylim(lo_y, hi_y)
    ax[0].set_title(f"1H 0707-495, 0.3-1 vs 1-4 keV: {M} segments x {A['segment_s']/1e3:.0f} ks, "
                    f"{A['timing_gti']}, PATTERN<={L['pattern_max']}", fontsize=10)
    ci = np.array([r["coh_intrinsic"] for r in rows])
    cie = np.array([r["coh_intrinsic_err"] for r in rows])
    cr = np.array([r["coh_raw"] for r in rows])
    ax[1].errorbar(fm, ci, yerr=cie, fmt="o", ms=4, color="k", lw=1, label="intrinsic (VN97 eq. 8)")
    ax[1].plot(fm, cr, "s", ms=3, color="tab:blue", label="raw")
    ax[1].set_ylim(-0.1, 1.3)
    ax[1].set_ylabel("coherence")
    ax[1].set_xlabel("frequency (Hz)")
    ax[1].legend(fontsize=8)
    ax[1].set_xlim(fm.min() / 1.5, 0.06)
    plt.tight_layout()
    plt.savefig(ROOT / "analysis/lags/lag_frequency.png", dpi=110)
    plt.close(fig)

    # keep the unbinned spectra for later stages / verification
    np.savez(OUT / "unbinned_cross_spectrum.npz", freq=f, cross=C, power_soft=PS, power_hard=PH, n_segments=M)
    print(json.dumps({k: summary[k] for k in ("n_segments", "high_freq_mean_lag", "low_freq_mean_lag",
                                             "positive_to_negative_crossing_hz", "self_test_sign",
                                             "stingray_cross_check")}, indent=2))
    if not (test["passed"] and srchk["passed"]):
        raise SystemExit("self-test or Stingray cross-check FAILED; see summary.json")


if __name__ == "__main__":
    main()

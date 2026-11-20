#!/usr/bin/env python3
"""Re-derive R1 and R3 from the written method, starting from the raw event lists.

R1 is the 0.3–1 keV versus 1–4 keV lag–frequency spectrum.
R3 is the net EPIC-pn exposure after the flare screen.

This file is an independent implementation. It does not import or read
reduction/filter/filter.py, analysis/lightcurves/lightcurves.py, or
analysis/lags/lags.py. Parameters come from params.yaml. Choices the written
record leaves open are marked V-01 … V-09 in ASSUMPTIONS.md.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from astropy.io import fits
from stingray.fourier import intrinsic_coherence

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "outputs"
DT = 10.0  # s, A-06
SEGMENT_BINS = None  # set from params in main


def log(msg: str) -> None:
    print(msg, flush=True)


def angsep_arcsec(ra1, dec1, ra2, dec2):
    """Great-circle separation in arcsec. Angles in degrees."""
    ra1, dec1, ra2, dec2 = map(np.deg2rad, (ra1, dec1, ra2, dec2))
    dra = ra2 - ra1
    ddec = dec2 - dec1
    a = np.sin(ddec / 2.0) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin(dra / 2.0) ** 2
    return np.rad2deg(2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))) * 3600.0


def mean_radec(ra_deg, dec_deg):
    ra = np.deg2rad(np.asarray(ra_deg, dtype=float))
    dec = np.deg2rad(np.asarray(dec_deg, dtype=float))
    x = np.mean(np.cos(dec) * np.cos(ra))
    y = np.mean(np.cos(dec) * np.sin(ra))
    z = np.mean(np.sin(dec))
    hyp = math.hypot(x, y)
    dec_m = math.degrees(math.atan2(z, hyp))
    ra_m = math.degrees(math.atan2(y, x)) % 360.0
    return ra_m, dec_m


class TanWCS:
    """EVENTS X/Y TAN projection from the REFX*/REFY* keywords. V-04."""

    def __init__(self, hdr):
        self.crpix_x = float(hdr["REFXCRPX"])
        self.crval_x = float(hdr["REFXCRVL"])
        self.cdelt_x = float(hdr["REFXCDLT"])
        self.crpix_y = float(hdr["REFYCRPX"])
        self.crval_y = float(hdr["REFYCRVL"])
        self.cdelt_y = float(hdr["REFYCDLT"])
        if hdr.get("REFXCTYP", "RA---TAN") != "RA---TAN":
            raise RuntimeError(f"unexpected REFXCTYP {hdr.get('REFXCTYP')}")
        if hdr.get("REFYCTYP", "DEC--TAN") != "DEC--TAN":
            raise RuntimeError(f"unexpected REFYCTYP {hdr.get('REFYCTYP')}")

    def xy_to_radec(self, x, y):
        xi = np.deg2rad((np.asarray(x, dtype=float) - self.crpix_x) * self.cdelt_x)
        eta = np.deg2rad((np.asarray(y, dtype=float) - self.crpix_y) * self.cdelt_y)
        ra0 = math.radians(self.crval_x)
        dec0 = math.radians(self.crval_y)
        rho = np.sqrt(xi * xi + eta * eta)
        small = rho < 1e-15
        rho_safe = np.where(small, 1.0, rho)
        c = np.arctan(rho)
        sin_c = np.sin(c)
        cos_c = np.cos(c)
        dec = np.arcsin(
            np.clip(cos_c * math.sin(dec0) + eta * sin_c * math.cos(dec0) / rho_safe, -1, 1)
        )
        ra = ra0 + np.arctan2(
            xi * sin_c / rho_safe,
            cos_c * math.cos(dec0) - eta * sin_c * math.sin(dec0) / rho_safe,
        )
        ra = np.where(small, ra0, ra)
        dec = np.where(small, dec0, dec)
        return np.rad2deg(ra) % 360.0, np.rad2deg(dec)

    def radec_to_xy(self, ra_deg, dec_deg):
        ra = np.deg2rad(np.asarray(ra_deg, dtype=float))
        dec = np.deg2rad(np.asarray(dec_deg, dtype=float))
        ra0 = math.radians(self.crval_x)
        dec0 = math.radians(self.crval_y)
        cosc = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(ra - ra0)
        xi = np.cos(dec) * np.sin(ra - ra0) / cosc
        eta = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(ra - ra0)) / cosc
        x = self.crpix_x + np.rad2deg(xi) / self.cdelt_x
        y = self.crpix_y + np.rad2deg(eta) / self.cdelt_y
        return x, y

    def xy_to_tangent_arcsec(self, x, y):
        """Offsets from the WCS reference point, arcsec, on the tangent plane."""
        dx = (np.asarray(x, dtype=float) - self.crpix_x) * self.cdelt_x * 3600.0
        dy = (np.asarray(y, dtype=float) - self.crpix_y) * self.cdelt_y * 3600.0
        return dx, dy

    def tangent_arcsec_to_xy(self, dx, dy):
        x = self.crpix_x + np.asarray(dx, dtype=float) / (self.cdelt_x * 3600.0)
        y = self.crpix_y + np.asarray(dy, dtype=float) / (self.cdelt_y * 3600.0)
        return x, y


def overlap_duration(a, b) -> float:
    """Total length of the intersection of two lists of [start, stop) intervals."""
    total = 0.0
    for s1, e1 in a:
        for s2, e2 in b:
            total += max(0.0, min(e1, e2) - max(s1, s2))
    return total


def fracexp_of_bins(t0, n_bins, dt, gtis):
    frac = np.zeros(n_bins, dtype=float)
    for s, e in gtis:
        i0 = max(0, int(math.floor((s - t0) / dt)))
        i1 = min(n_bins, int(math.ceil((e - t0) / dt)))
        for i in range(i0, i1):
            bs = t0 + i * dt
            be = bs + dt
            frac[i] += max(0.0, min(be, e) - max(bs, s))
    frac /= dt
    # A bin can touch two GTIs; clip numerical overshoot.
    return np.clip(frac, 0.0, 1.0)


def fill_short_gaps(values, is_gap, max_gap_s, dt):
    """Linearly fill gaps of at most max_gap_s. V-06.

    A short gap with only one neighbour (the segment edge) is held at the
    nearest good sample. A longer gap is left untouched and reported.
    """
    out = np.array(values, dtype=float, copy=True)
    n = len(out)
    filled = 0
    held = 0
    long_gaps = []
    i = 0
    max_bins = int(math.floor(max_gap_s / dt + 1e-9))
    while i < n:
        if not is_gap[i]:
            i += 1
            continue
        j = i
        while j < n and is_gap[j]:
            j += 1
        length = j - i
        left = i - 1
        right = j  # first good bin after the gap, or n
        has_left = left >= 0 and not is_gap[left]
        has_right = right < n and not is_gap[right]
        if length <= max_bins and has_left and has_right:
            y0 = out[left]
            y1 = out[right]
            span = right - left
            for k in range(i, j):
                out[k] = y0 + (y1 - y0) * ((k - left) / span)
            filled += length
        elif length <= max_bins and (has_left or has_right):
            anchor = out[left] if has_left else out[right]
            out[i:j] = anchor
            held += length
        else:
            long_gaps.append({"i0": int(i), "i1": int(j), "n_bins": int(length)})
        i = j
    return out, filled, held, long_gaps


def iterative_centroid(ra, dec, ra0, dec0, radius_arcsec=20.0):
    """Mean position of events inside a moving circle. V-04. A-03."""
    center = (float(ra0), float(dec0))
    n_used = 0
    shift = None
    for _ in range(30):
        sep = angsep_arcsec(center[0], center[1], ra, dec)
        sel = sep <= radius_arcsec
        n_used = int(sel.sum())
        if n_used < 10:
            raise RuntimeError(f"centroid has only {n_used} events within {radius_arcsec} arcsec")
        new = mean_radec(ra[sel], dec[sel])
        shift = float(angsep_arcsec(center[0], center[1], new[0], new[1]))
        center = new
        if shift < 0.001:
            break
    return center, n_used, shift


def affine_fit(dx, dy, raw):
    design = np.column_stack([np.ones(dx.size), dx, dy])
    coef, _, _, _ = np.linalg.lstsq(design, raw.astype(float), rcond=None)
    pred = design @ coef
    rms = float(np.sqrt(np.mean((raw.astype(float) - pred) ** 2)))
    return coef, rms


def apply_affine(coef_x, coef_y, dx, dy):
    rawx = coef_x[0] + coef_x[1] * dx + coef_x[2] * dy
    rawy = coef_y[0] + coef_y[1] * dx + coef_y[2] * dy
    return rawx, rawy


def invert_affine(coef_x, coef_y, rawx, rawy):
    matrix = np.array(
        [[coef_x[1], coef_x[2]], [coef_y[1], coef_y[2]]],
        dtype=float,
    )
    rhs = np.array([rawx - coef_x[0], rawy - coef_y[0]], dtype=float)
    dx, dy = np.linalg.solve(matrix, rhs)
    return float(dx), float(dy)


def circle_area_on_mask(dx0, dy0, coef_x, coef_y, good, radius=35.0, step=0.5):
    """0.5 arcsec grid. A point counts when its nearest RAW pixel is good. V-05."""
    axis = np.arange(-radius, radius + 1e-9, step)
    xx, yy = np.meshgrid(axis, axis, indexing="xy")
    keep = xx * xx + yy * yy <= radius * radius
    dx = dx0 + xx[keep]
    dy = dy0 + yy[keep]
    rawx, rawy = apply_affine(coef_x, coef_y, dx, dy)
    ix = np.rint(rawx).astype(int)
    iy = np.rint(rawy).astype(int)
    on = np.array(
        [int(ix[i]) in good and int(iy[i]) in good[int(ix[i])] for i in range(ix.size)],
        dtype=bool,
    )
    n_on = int(on.sum())
    area = n_on * step * step
    return area, int(keep.sum()), n_on


def histogram_bins(time, t0, n_bins, dt):
    idx = np.floor((time - t0) / dt).astype(np.int64)
    ok = (idx >= 0) & (idx < n_bins)
    counts = np.bincount(idx[ok], minlength=n_bins)
    return counts[:n_bins]


def load_exposure(path):
    log(f"reading {path}")
    with fits.open(path, memmap=False) as hdul:
        hdr = hdul["EVENTS"].header
        rec = hdul["EVENTS"].data
        gti_rec = hdul["STDGTI04"].data
        cols = {
            "time": np.asarray(rec["TIME"], dtype=np.float64),
            "rawx": np.asarray(rec["RAWX"], dtype=np.int16),
            "rawy": np.asarray(rec["RAWY"], dtype=np.int16),
            "x": np.asarray(rec["X"], dtype=np.float64),
            "y": np.asarray(rec["Y"], dtype=np.float64),
            "pi": np.asarray(rec["PI"], dtype=np.int32),
            "flag": np.asarray(rec["FLAG"], dtype=np.int32),
            "pattern": np.asarray(rec["PATTERN"], dtype=np.int16),
            "ccdnr": np.asarray(rec["CCDNR"], dtype=np.int16),
        }
        gtis = np.column_stack(
            [
                np.asarray(gti_rec["START"], dtype=np.float64),
                np.asarray(gti_rec["STOP"], dtype=np.float64),
            ]
        )
    return hdr, cols, gtis


def process_exposure(path, filt, lc_params):
    hdr, c, gtis = load_exposure(path)
    wcs = TanWCS(hdr)
    # Sanity: the reference pixel must map back to the reference sky position.
    x_ref, y_ref = wcs.radec_to_xy(wcs.crval_x, wcs.crval_y)
    if abs(x_ref - wcs.crpix_x) > 1e-4 or abs(y_ref - wcs.crpix_y) > 1e-4:
        raise RuntimeError("WCS round trip of the reference pixel failed")

    ra_obj = float(hdr["RA_OBJ"])
    dec_obj = float(hdr["DEC_OBJ"])
    t0 = float(gtis[:, 0].min())
    t1 = float(gtis[:, 1].max())
    gti_list = [(float(s), float(e)) for s, e in gtis]

    flag0 = c["flag"] == 0
    # Centroid sample: any CCD, FLAG==0, PATTERN<=4, 0.3–10 keV closed (V-02).
    cen_sel = flag0 & (c["pattern"] <= 4) & (c["pi"] >= 300) & (c["pi"] <= 10000)
    ra_c, dec_c = wcs.xy_to_radec(c["x"][cen_sel], c["y"][cen_sel])
    (ra_s, dec_s), n_cen, shift = iterative_centroid(ra_c, dec_c, ra_obj, dec_obj, filt["centroid_radius_arcsec"])
    offset = float(angsep_arcsec(ra_obj, dec_obj, ra_s, dec_s))

    # Affine sky ↔ RAW on CCD 4, FLAG==0 (V-05).
    ccd4 = c["ccdnr"] == 4
    fit_sel = ccd4 & flag0
    dx_fit, dy_fit = wcs.xy_to_tangent_arcsec(c["x"][fit_sel], c["y"][fit_sel])
    coef_x, rms_x = affine_fit(dx_fit, dy_fit, c["rawx"][fit_sel])
    coef_y, rms_y = affine_fit(dx_fit, dy_fit, c["rawy"][fit_sel])

    x_s, y_s = wcs.radec_to_xy(ra_s, dec_s)
    dx_s, dy_s = wcs.xy_to_tangent_arcsec(x_s, y_s)
    rawx_s, rawy_s = apply_affine(coef_x, coef_y, dx_s, dy_s)
    rawx_b = float(rawx_s) + float(filt["bkg_drawx"])
    rawy_b = float(rawy_s)
    dx_b, dy_b = invert_affine(coef_x, coef_y, rawx_b, rawy_b)
    x_b, y_b = wcs.tangent_arcsec_to_xy(dx_b, dy_b)
    ra_b, dec_b = wcs.xy_to_radec(x_b, y_b)
    ra_b, dec_b = float(np.asarray(ra_b)), float(np.asarray(dec_b))

    rx = c["rawx"][fit_sel]
    ry = c["rawy"][fit_sel]
    pixels = np.unique(np.column_stack([rx, ry]), axis=0)
    good = {}
    for px, py in pixels:
        good.setdefault(int(px), set()).add(int(py))

    area_src, n_grid, n_src_on = circle_area_on_mask(float(dx_s), float(dy_s), coef_x, coef_y, good, filt["src_radius_arcsec"])
    area_bkg, _, n_bkg_on = circle_area_on_mask(dx_b, dy_b, coef_x, coef_y, good, filt["bkg_radius_arcsec"])
    backrat = float(area_src / area_bkg) if area_bkg > 0 else float("nan")

    # Sky box of ±2 arcmin around the centroid, then a great-circle cut.
    # 0.05 arcsec per X/Y pixel, so 2 arcmin is 2400 pixels; 4000 leaves margin.
    x_cen, y_cen = wcs.radec_to_xy(ra_s, dec_s)
    box = (np.abs(c["x"] - float(x_cen)) < 4000.0) & (np.abs(c["y"] - float(y_cen)) < 4000.0)
    ra_box, dec_box = wcs.xy_to_radec(c["x"][box], c["y"][box])
    sep_src = angsep_arcsec(ra_s, dec_s, ra_box, dec_box)
    sep_bkg = angsep_arcsec(ra_b, dec_b, ra_box, dec_box)
    box_idx = np.flatnonzero(box)
    src_idx = box_idx[sep_src <= filt["src_radius_arcsec"]]
    bkg_idx = box_idx[sep_bkg <= filt["bkg_radius_arcsec"]]
    src_ccd_frac = float(np.mean(c["ccdnr"][src_idx] == 4)) if src_idx.size else 0.0

    # Flare screen, full field (A-05, V-01, V-02, V-03).
    flare = filt["flare"]
    flare_sel = (
        flag0
        & (c["pattern"] == int(flare["pattern"]))
        & (c["pi"] >= int(flare["pi_min"]))
        & (c["pi"] <= int(flare["pi_max"]))
    )
    bin_s = float(flare["bin_s"])
    n_flare = int(math.floor((t1 - t0) / bin_s))
    flare_counts = histogram_bins(c["time"][flare_sel], t0, n_flare, bin_s)
    flare_rate = flare_counts / bin_s
    good_flare = flare_rate < float(flare["threshold_cps"])
    flare_gtis = [
        (t0 + i * bin_s, t0 + (i + 1) * bin_s) for i in range(n_flare) if good_flare[i]
    ]
    flare_duration = float(good_flare.sum() * bin_s)
    net_intersect = overlap_duration(flare_gtis, gti_list)
    stdgti_duration = float(sum(e - s for s, e in gti_list))

    # Light-curve grid on the same t0 (A-06, V-03).
    dt = float(lc_params["dt_s"])
    n_bins = int(math.floor((t1 - t0) / dt))
    frac = fracexp_of_bins(t0, n_bins, dt, gti_list)
    pattern_max = int(lc_params["pattern_max"])
    soft_lo, soft_hi = lc_params["bands_kev"]["soft"]
    hard_lo, hard_hi = lc_params["bands_kev"]["hard"]
    # PI in [lo, hi) eV, as the light-curve method states.
    base = flag0 & (c["pattern"] <= pattern_max)

    def band_counts(idx, lo_kev, hi_kev):
        if idx.size == 0:
            return np.zeros(n_bins, dtype=np.int64)
        pi = c["pi"][idx]
        sel = base[idx] & (pi >= int(round(lo_kev * 1000))) & (pi < int(round(hi_kev * 1000)))
        return histogram_bins(c["time"][idx][sel], t0, n_bins, dt)

    src_soft = band_counts(src_idx, soft_lo, soft_hi)
    src_hard = band_counts(src_idx, hard_lo, hard_hi)
    bkg_soft = band_counts(bkg_idx, soft_lo, soft_hi)
    bkg_hard = band_counts(bkg_idx, hard_lo, hard_hi)

    info = {
        "t0": t0,
        "t1": t1,
        "span_s": t1 - t0,
        "stdgti_duration_s": stdgti_duration,
        "n_stdgti": len(gti_list),
        "ra_obj": ra_obj,
        "dec_obj": dec_obj,
        "ra_src": ra_s,
        "dec_src": dec_s,
        "centroid_offset_arcsec": offset,
        "centroid_n": n_cen,
        "centroid_last_shift_arcsec": shift,
        "rawx_src": float(rawx_s),
        "rawy_src": float(rawy_s),
        "rawx_bkg": rawx_b,
        "rawy_bkg": rawy_b,
        "affine_rms_rawx": rms_x,
        "affine_rms_rawy": rms_y,
        "n_fit_events": int(fit_sel.sum()),
        "area_src_arcsec2": area_src,
        "area_bkg_arcsec2": area_bkg,
        "n_grid": n_grid,
        "n_src_grid_on": n_src_on,
        "n_bkg_grid_on": n_bkg_on,
        "backrat": backrat,
        "src_ccd4_fraction": src_ccd_frac,
        "n_src_events_any_pi": int(src_idx.size),
        "flare_n_bins": n_flare,
        "flare_n_good_bins": int(good_flare.sum()),
        "flare_good_duration_s": flare_duration,
        "net_intersect_stdgti_s": net_intersect,
        "flare_rate_median": float(np.median(flare_rate)) if flare_rate.size else None,
        "flare_rate_max": float(flare_rate.max()) if flare_rate.size else None,
        "src_soft_counts": int(src_soft.sum()),
        "src_hard_counts": int(src_hard.sum()),
        "bkg_soft_counts": int(bkg_soft.sum()),
        "bkg_hard_counts": int(bkg_hard.sum()),
    }
    lc = {
        "t0": t0,
        "dt": dt,
        "n_bins": n_bins,
        "frac": frac,
        "src_soft": src_soft,
        "src_hard": src_hard,
        "bkg_soft": bkg_soft,
        "bkg_hard": bkg_hard,
        "backrat": backrat,
        "flare_gtis": np.array(flare_gtis, dtype=float),
    }
    return info, lc


def choose_window(lc, segment_s):
    """Earliest 100 ks block of bins that minimises time outside the flare GTIs. V-03."""
    dt = lc["dt"]
    n_seg = int(round(segment_s / dt))
    if abs(n_seg * dt - segment_s) > 1e-6:
        raise RuntimeError("segment length is not an integer number of light-curve bins")
    n_bins = lc["n_bins"]
    if n_bins < n_seg:
        raise RuntimeError(f"exposure has {n_bins} bins, shorter than a {n_seg}-bin segment")
    flare = [tuple(row) for row in lc["flare_gtis"]]
    best = None
    for i0 in range(n_bins - n_seg + 1):
        ws = lc["t0"] + i0 * dt
        we = ws + segment_s
        outside = segment_s - overlap_duration([(ws, we)], flare)
        # Tie: earlier window. 1 ms absorbs floating-point dust (V-03).
        if best is None or outside < best[0] - 1e-3 or (abs(outside - best[0]) <= 1e-3 and i0 < best[1]):
            best = (outside, i0, ws)
    outside, i0, ws = best
    return {
        "i0": int(i0),
        "start_offset_s": float(ws - lc["t0"]),
        "t_start": float(ws),
        "t_stop": float(ws + segment_s),
        "time_outside_flare_s": float(outside),
        "n_bins": n_seg,
    }


def segment_series(lc, window, max_gap_s, background_subtract):
    i0 = window["i0"]
    i1 = i0 + window["n_bins"]
    sl = slice(i0, i1)
    frac = lc["frac"][sl]
    is_gap = frac < 1e-6
    backrat = lc["backrat"] if background_subtract else 0.0
    bands = {}
    noise = {}
    gap_info = {}
    for name in ("soft", "hard"):
        src = lc[f"src_{name}"][sl].astype(float)
        bkg = lc[f"bkg_{name}"][sl].astype(float)
        net = src - backrat * bkg
        filled, n_fill, n_hold, long_gaps = fill_short_gaps(net, is_gap, max_gap_s, lc["dt"])
        if long_gaps:
            raise RuntimeError(f"gap longer than {max_gap_s} s in {name}: {long_gaps}")
        bands[name] = filled
        # Sum of per-bin count variances. Gap bins contribute 0 (V-06).
        noise[name] = float(np.sum(src + (backrat ** 2) * bkg))
        gap_info[name] = {"filled_bins": int(n_fill), "held_edge_bins": int(n_hold)}
    return bands, noise, gap_info, int(is_gap.sum())


def bin_cross_spectrum(segments, noises, dt, freq_bin_factor):
    """Average conj(H)*S, |S|² and |H|², then geometric frequency bins. V-07."""
    n_seg = len(segments)
    n = segments[0]["soft"].size
    freqs = np.fft.rfftfreq(n, d=dt)
    nyquist = 0.5 / dt
    c_acc = None
    ps_acc = None
    ph_acc = None
    for seg in segments:
        soft = seg["soft"] - np.mean(seg["soft"])
        hard = seg["hard"] - np.mean(seg["hard"])
        s_ft = np.fft.rfft(soft)
        h_ft = np.fft.rfft(hard)
        cross = np.conj(h_ft) * s_ft
        ps = (s_ft.real ** 2 + s_ft.imag ** 2)
        ph = (h_ft.real ** 2 + h_ft.imag ** 2)
        c_acc = cross if c_acc is None else c_acc + cross
        ps_acc = ps if ps_acc is None else ps_acc + ps
        ph_acc = ph if ph_acc is None else ph_acc + ph
    c_mean = c_acc / n_seg
    ps_mean = ps_acc / n_seg
    ph_mean = ph_acc / n_seg
    noise_s = float(np.mean([n["soft"] for n in noises]))
    noise_h = float(np.mean([n["hard"] for n in noises]))

    # Positive frequencies strictly below Nyquist.
    use = (freqs > 0) & (freqs < nyquist - 1e-15)
    f = freqs[use]
    c_mean = c_mean[use]
    ps_mean = ps_mean[use]
    ph_mean = ph_mean[use]

    f_min = 1.0 / (n * dt)
    edges = [f_min]
    while edges[-1] * freq_bin_factor <= nyquist + 1e-12:
        edges.append(edges[-1] * freq_bin_factor)
    edges = np.asarray(edges, dtype=float)

    rows = []
    n_empty = 0
    for i in range(len(edges) - 1):
        flo, fhi = float(edges[i]), float(edges[i + 1])
        sel = (f >= flo) & (f < fhi)
        n_freq = int(sel.sum())
        if n_freq == 0:
            n_empty += 1
            continue
        cc = np.mean(c_mean[sel])
        ps = float(np.mean(ps_mean[sel]))
        ph = float(np.mean(ph_mean[sel]))
        k = n_seg * n_freq
        f_mean = float(np.mean(f[sel]))
        raw = float((cc.real ** 2 + cc.imag ** 2) / (ps * ph)) if ps > 0 and ph > 0 else float("nan")
        raw_clip = float(np.clip(raw, 0.0, 1.0)) if np.isfinite(raw) else float("nan")
        if np.isfinite(raw_clip) and raw_clip > 0:
            phase_err = math.sqrt((1.0 - raw_clip) / (2.0 * raw_clip * k))
        else:
            phase_err = float("inf")
        phase = float(np.angle(cc))
        lag = phase / (2.0 * math.pi * f_mean)
        lag_err = phase_err / (2.0 * math.pi * f_mean)
        ic, ic_err = intrinsic_coherence(
            cc, ps, ph, noise_s, noise_h, k, return_uncertainty=True, adjust_bias=False
        )
        ic = float(ic)
        ic_err = float(ic_err)
        reliable = bool(np.isfinite(ic) and k >= 30)
        rows.append(
            {
                "f_lo_hz": flo,
                "f_hi_hz": fhi,
                "f_mean_hz": f_mean,
                "f_geom_hz": math.sqrt(flo * fhi),
                "n_freq": n_freq,
                "K": int(k),
                "lag_s": lag,
                "lag_err_s": lag_err if np.isfinite(lag_err) else None,
                "phase_rad": phase,
                "coherence_raw": raw,
                "coherence_intrinsic": ic if np.isfinite(ic) else None,
                "coherence_intrinsic_err": ic_err if np.isfinite(ic_err) else None,
                "reliable": reliable,
                "noise_soft": noise_s,
                "noise_hard": noise_h,
            }
        )
    return rows, {"n_empty_bins": n_empty, "n_segments": n_seg, "n_time": n, "nyquist_hz": nyquist}


def inverse_variance_mean(rows, f_lo, f_hi):
    lags = []
    errs = []
    for row in rows:
        if not row["reliable"]:
            continue
        if row["lag_err_s"] is None or not (f_lo <= row["f_mean_hz"] < f_hi):
            continue
        if row["lag_err_s"] <= 0:
            continue
        lags.append(row["lag_s"])
        errs.append(row["lag_err_s"])
    if not lags:
        return {"n": 0, "lag_s": None, "lag_err_s": None}
    lags = np.asarray(lags)
    errs = np.asarray(errs)
    w = 1.0 / errs ** 2
    mean = float(np.sum(w * lags) / np.sum(w))
    err = float(math.sqrt(1.0 / np.sum(w)))
    return {"n": int(lags.size), "lag_s": mean, "lag_err_s": err, "f_lo_hz": f_lo, "f_hi_hz": f_hi}


def self_test(dt, segment_s, freq_bin_factor):
    """Hard band delayed by +30 s. The method's tolerance is 1 s. V-07."""
    rng = np.random.default_rng(12345)
    n = int(round(segment_s / dt))
    shift = int(round(30.0 / dt))
    segments = []
    noises = []
    for _ in range(4):
        soft = rng.normal(0.0, 1.0, size=n)
        hard = np.roll(soft, shift)
        segments.append({"soft": soft, "hard": hard})
        noises.append({"soft": 0.0, "hard": 0.0})
    rows, meta = bin_cross_spectrum(segments, noises, dt, freq_bin_factor)
    lags = [r["lag_s"] for r in rows if 1e-4 <= r["f_mean_hz"] <= 3e-3]
    median = float(np.median(lags))
    passed = abs(median - 30.0) <= 1.0 and median > 0
    return {"median_lag_s": median, "n_bins_in_range": len(lags), "passed": passed, "tolerance_s": 1.0, **meta}


def write_csv(path, rows):
    cols = [
        "f_lo_hz",
        "f_hi_hz",
        "f_mean_hz",
        "f_geom_hz",
        "n_freq",
        "K",
        "lag_s",
        "lag_err_s",
        "phase_rad",
        "coherence_raw",
        "coherence_intrinsic",
        "coherence_intrinsic_err",
        "reliable",
    ]
    with path.open("w", newline="\n") as fh:
        fh.write(",".join(cols) + "\n")
        for row in rows:
            vals = []
            for col in cols:
                v = row[col]
                if v is None:
                    vals.append("")
                elif isinstance(v, bool):
                    vals.append("1" if v else "0")
                elif isinstance(v, int):
                    vals.append(str(v))
                else:
                    vals.append(repr(float(v)))
            fh.write(",".join(vals) + "\n")


def jsonable(obj):
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (REPO / "params.yaml").open() as fh:
        params = yaml.safe_load(fh)
    filt = params["filter"]
    lc_params = params["lightcurves"]
    lag_params = params["lags"]
    if lag_params["timing_gti"] != "orbit":
        raise RuntimeError("this re-derivation implements timing_gti=orbit only")

    test = self_test(float(lc_params["dt_s"]), float(lag_params["segment_s"]), float(lag_params["freq_bin_factor"]))
    log(f"self-test median lag {test['median_lag_s']:.6f} s, passed={test['passed']}")
    if not test["passed"]:
        raise RuntimeError(f"sign self-test failed: {test}")

    files = {
        ("0511580101", "PNS001"): REPO / "reduction/raw/0511580101/P0511580101PNS001PIEVLI0000.FTZ",
        ("0511580201", "PNS001"): REPO / "reduction/raw/0511580201/P0511580201PNS001PIEVLI0000.FTZ",
        ("0511580201", "PNU027"): REPO / "reduction/raw/0511580201/P0511580201PNU027PIEVLI0000.FTZ",
        ("0511580301", "PNU002"): REPO / "reduction/raw/0511580301/P0511580301PNU002PIEVLI0000.FTZ",
        ("0511580401", "PNU002"): REPO / "reduction/raw/0511580401/P0511580401PNU002PIEVLI0000.FTZ",
    }

    per_exp = []
    segments = []
    noises = []
    r3 = 0.0
    r3_bins_only = 0.0
    for exp in params["exposures"]:
        key = (exp["obsid"], exp["expo"])
        if not exp["include"]:
            log(f"skip {key[0]} {key[1]} (include: false, A-01)")
            continue
        info, lc = process_exposure(files[key], filt, lc_params)
        if info["src_ccd4_fraction"] < 0.99:
            raise RuntimeError(f"source circle is not on CCD 4: {info['src_ccd4_fraction']}")
        window = choose_window(lc, float(lag_params["segment_s"]))
        bands, noise, gap_info, n_gap = segment_series(
            lc,
            window,
            float(lag_params["max_gap_fill_s"]),
            bool(lag_params["background_subtract"]),
        )
        info["window"] = window
        info["gap_bins"] = n_gap
        info["gap_fill"] = gap_info
        info["noise_soft"] = noise["soft"]
        info["noise_hard"] = noise["hard"]
        per_exp.append({"obsid": key[0], "expo": key[1], **info})
        segments.append(bands)
        noises.append(noise)
        r3 += info["net_intersect_stdgti_s"]
        r3_bins_only += info["flare_good_duration_s"]
        log(
            f"{key[0]} {key[1]}: offset {info['centroid_offset_arcsec']:.3f} arcsec, "
            f"RAW ({info['rawx_src']:.2f}, {info['rawy_src']:.2f}), "
            f"BACKRAT {info['backrat']:.6f}, rms ({info['affine_rms_rawx']:.3f}, {info['affine_rms_rawy']:.3f}) px, "
            f"net {info['net_intersect_stdgti_s']/1000:.3f} ks, "
            f"window +{window['start_offset_s']/1000:.3f} ks, outside {window['time_outside_flare_s']/1000:.3f} ks, "
            f"gap bins {n_gap}"
        )

    rows, meta = bin_cross_spectrum(segments, noises, float(lc_params["dt_s"]), float(lag_params["freq_bin_factor"]))
    hf = inverse_variance_mean(rows, 7e-4, 5e-3)
    n_rel = sum(1 for r in rows if r["reliable"])
    summary = {
        "r3_net_exposure_s": r3,
        "r3_net_exposure_ks": r3 / 1000.0,
        "r3_definition": (
            "Sum over the four included exposures of the duration of the intersection "
            "of flare-good 100 s bins (full-field rate < 0.4 c/s) with the CCD-4 standard GTIs."
        ),
        "r3_flare_bins_only_s": r3_bins_only,
        "r3_flare_bins_only_ks": r3_bins_only / 1000.0,
        "r1_n_bins": len(rows),
        "r1_n_reliable": n_rel,
        "r1_high_frequency_mean": hf,
        "r1_fourier": meta,
        "self_test": test,
        "exposures": per_exp,
        "libraries": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "stingray": __import__("stingray").__version__,
            "astropy": __import__("astropy").__version__,
        },
    }
    write_csv(OUT / "r1_lag_frequency.csv", rows)
    with (OUT / "r1_r3_summary.json").open("w") as fh:
        json.dump(jsonable(summary), fh, indent=2)
        fh.write("\n")
    log(
        f"R3 = {r3/1000:.6f} ks (intersection), {r3_bins_only/1000:.6f} ks (good bins only); "
        f"R1 bins {len(rows)}, reliable {n_rel}; "
        f"high-frequency mean {hf['lag_s']} ± {hf['lag_err_s']} s (n={hf['n']})"
    )
    log(f"wrote {OUT}")


if __name__ == "__main__":
    main()

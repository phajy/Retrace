#!/usr/bin/env python3
"""Stage 2 (filter): event selection, source/background regions and flare GTIs.

Reduction v0. Starts from the PPS calibrated EPIC-pn event lists and uses
numpy/astropy only (no SAS). For each exposure listed in params.yaml it:

  1. finds the source position (iterative centroid of the events, starting at RA_OBJ/DEC_OBJ);
  2. selects source events in a 35" circle and background events in a circle on the
     same CCD at the same RAWY (same distance from the readout node);
  3. computes the effective (unflagged) area of both regions, which gives the background scaling;
  4. builds a classic flare light curve (full field, single events, 10-12 keV) and
     flare GTIs from a count-rate threshold;
  5. writes one FITS file per exposure with source/background events and all the GTI
     tables (CCD standard GTIs, flare GTIs, their intersection, and the PPS optimised GTIs),
     plus diagnostic plots, a summary (summary.json) and content hashes of every data column.

Events are NOT cut by the flare GTIs here. The light-curve stage applies the chosen GTI,
so that sensitivity tests (different flare handling) do not need this stage to be re-run.

Usage:  python reduction/filter/filter.py        (normally run via `dvc repro filter`)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np
import yaml
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "reduction" / "raw"
OUT = ROOT / "reduction" / "filter" / "output"

EV_COLS = ["TIME", "RAWX", "RAWY", "X", "Y", "PI", "FLAG", "PATTERN", "CCDNR"]


# --------------------------------------------------------------------------- helpers
def gti_intersect(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Intersection of two GTI lists, each an (N, 2) array of [start, stop]."""
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        lo = max(a[i, 0], b[j, 0])
        hi = min(a[i, 1], b[j, 1])
        if hi > lo:
            out.append((lo, hi))
        if a[i, 1] < b[j, 1]:
            i += 1
        else:
            j += 1
    return np.array(out, dtype=float).reshape(-1, 2)


def in_gti(t: np.ndarray, gti: np.ndarray) -> np.ndarray:
    m = np.zeros(t.shape, dtype=bool)
    for lo, hi in gti:
        m |= (t >= lo) & (t < hi)
    return m


def runs_to_gti(good: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Turn a boolean per-bin mask into GTIs using the bin edges."""
    out = []
    start = None
    for k, g in enumerate(good):
        if g and start is None:
            start = edges[k]
        if not g and start is not None:
            out.append((start, edges[k]))
            start = None
    if start is not None:
        out.append((start, edges[len(good)]))
    return np.array(out, dtype=float).reshape(-1, 2)


def column_hashes(table: Table) -> dict:
    """sha256 of each column's values in a canonical big-endian layout (content, not file bytes)."""
    h = {}
    for name in table.colnames:
        arr = np.asarray(table[name])
        arr = np.ascontiguousarray(arr.astype(arr.dtype.newbyteorder(">")))
        h[name] = hashlib.sha256(arr.tobytes()).hexdigest()
    return h


def sky_wcs(hdr) -> WCS:
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix = [hdr["REFXCRPX"], hdr["REFYCRPX"]]
    w.wcs.crval = [hdr["REFXCRVL"], hdr["REFYCRVL"]]
    w.wcs.cdelt = [hdr["REFXCDLT"], hdr["REFYCDLT"]]
    return w


# --------------------------------------------------------------------------- per exposure
def process(obsid: str, expo: str, P: dict) -> dict:
    stem = f"P{obsid}{expo}"
    evfile = RAW / obsid / f"{stem}PIEVLI0000.FTZ"
    fbfile = RAW / obsid / f"{stem}FBKTSR0000.FTZ"

    with fits.open(evfile, memmap=False) as h:
        ev = {c: np.asarray(h["EVENTS"].data[c]) for c in EV_COLS}
        evh = h["EVENTS"].header
        prim = h[0].header
        stdgti = {}
        for hdu in h:
            if hdu.name.startswith("STDGTI"):
                ccd = int(hdu.name[6:])
                stdgti[ccd] = np.column_stack([hdu.data["START"], hdu.data["STOP"]]).astype(float)
    with fits.open(fbfile, memmap=False) as h:
        ppsgti = np.column_stack([h["SRC_GTIS"].data["START"], h["SRC_GTIS"].data["STOP"]]).astype(float)
        pps_thr = float(h["RATE"].header.get("FLCUTTHR", np.nan))

    pix = abs(evh["REFXCDLT"]) * 3600.0  # arcsec per sky pixel (0.05")
    w = sky_wcs(evh)
    F = P["filter"]

    # basic quality selection used for imaging and region work
    base = (ev["FLAG"] == F["flag"]) & (ev["PATTERN"] <= 4) & (ev["PI"] >= 300) & (ev["PI"] <= 10000)
    X = ev["X"].astype(float)
    Y = ev["Y"].astype(float)

    # 1. source centroid, starting at the proposal position
    ra_obj, dec_obj = float(prim["RA_OBJ"]), float(prim["DEC_OBJ"])
    (cx, cy), = w.wcs_world2pix([[ra_obj, dec_obj]], 1)
    rc = F["centroid_radius_arcsec"] / pix
    for _ in range(50):
        s = base & (np.hypot(X - cx, Y - cy) < rc)
        nx, ny = X[s].mean(), Y[s].mean()
        moved = np.hypot(nx - cx, ny - cy)
        cx, cy = nx, ny
        if moved < 1e-3:
            break
    (src_ra, src_dec), = w.wcs_pix2world([[cx, cy]], 1)
    offset_obj = float(np.hypot((src_ra - ra_obj) * np.cos(np.radians(dec_obj)), src_dec - dec_obj) * 3600)

    rs = F["src_radius_arcsec"] / pix
    in_src = np.hypot(X - cx, Y - cy) < rs
    ccds, n = np.unique(ev["CCDNR"][base & in_src], return_counts=True)
    src_ccd = int(ccds[np.argmax(n)])
    frac_on_ccd = float(n.max() / n.sum())

    # 2. sky <-> RAW affine map on the source CCD (RAW pixel 4.1" >> attitude jitter)
    on = (ev["CCDNR"] == src_ccd) & (ev["FLAG"] == F["flag"])
    idx = np.flatnonzero(on)[:: max(1, on.sum() // 300000)]
    A = np.column_stack([np.ones(idx.size), X[idx], Y[idx]])
    cRX, *_ = np.linalg.lstsq(A, ev["RAWX"][idx].astype(float), rcond=None)
    cRY, *_ = np.linalg.lstsq(A, ev["RAWY"][idx].astype(float), rcond=None)
    rms_rx = float(np.std(A @ cRX - ev["RAWX"][idx]))
    rms_ry = float(np.std(A @ cRY - ev["RAWY"][idx]))

    def sky_to_raw(x, y):
        return cRX[0] + cRX[1] * x + cRX[2] * y, cRY[0] + cRY[1] * x + cRY[2] * y

    M = np.array([[cRX[1], cRX[2]], [cRY[1], cRY[2]]])

    def raw_to_sky(rx, ry):
        return np.linalg.solve(M, np.array([rx - cRX[0], ry - cRY[0]]))

    src_rawx, src_rawy = sky_to_raw(cx, cy)
    bx, by = raw_to_sky(src_rawx + F["bkg_drawx"], src_rawy)
    rb = F["bkg_radius_arcsec"] / pix
    in_bkg = np.hypot(X - bx, Y - by) < rb
    sep_arcsec = float(np.hypot(bx - cx, by - cy) * pix)

    # 3. effective (unflagged) areas: deterministic grid in each circle, mapped to RAW pixels,
    #    looked up in a good-pixel mask (pixels that recorded FLAG==0 events on this CCD).
    good = np.zeros((66, 202), dtype=bool)
    good[ev["RAWX"][on], ev["RAWY"][on]] = True

    def eff_area(x0, y0, r):
        step = 0.5 / pix  # 0.5" grid
        g = np.arange(-r, r + step, step)
        gx, gy = np.meshgrid(g, g)
        k = gx**2 + gy**2 < r**2
        rx, ry = sky_to_raw(x0 + gx[k], y0 + gy[k])
        rx = np.rint(rx).astype(int)
        ry = np.rint(ry).astype(int)
        ok = (rx >= 0) & (rx < 66) & (ry >= 0) & (ry < 202)
        hit = np.zeros(rx.size, dtype=bool)
        hit[ok] = good[rx[ok], ry[ok]]
        frac = hit.mean()
        return float(np.pi * (r * pix) ** 2 * frac), float(frac)

    src_area, src_frac = eff_area(cx, cy, rs)
    bkg_area, bkg_frac = eff_area(bx, by, rb)
    backratio = src_area / bkg_area  # multiply background counts by this to scale to the source region

    # 4. classic flare light curve and GTIs
    Fl = F["flare"]
    fsel = (ev["FLAG"] == F["flag"]) & (ev["PATTERN"] == Fl["pattern"]) & \
           (ev["PI"] >= Fl["pi_min"]) & (ev["PI"] <= Fl["pi_max"])
    std = stdgti[src_ccd]
    t0, t1 = std[:, 0].min(), std[:, 1].max()
    nb = int(np.ceil((t1 - t0) / Fl["bin_s"]))
    edges = t0 + Fl["bin_s"] * np.arange(nb + 1)
    fcounts, _ = np.histogram(ev["TIME"][fsel], bins=edges)
    # exposure of each bin inside the standard GTI (bins half outside are rated on their GTI part)
    bexp = np.array([sum(max(0.0, min(hi, edges[k + 1]) - max(lo, edges[k])) for lo, hi in std)
                     for k in range(nb)])
    with np.errstate(divide="ignore", invalid="ignore"):
        frate = np.where(bexp > 0, fcounts / bexp, np.nan)
    good_bin = (bexp > 0) & (frate < Fl["threshold_cps"])
    flaregti = runs_to_gti(good_bin, edges)
    gti = gti_intersect(std, flaregti)

    def tot(g):
        return float(np.sum(g[:, 1] - g[:, 0])) if len(g) else 0.0

    # 5. outputs
    keep = (ev["FLAG"] == F["flag"]) & (ev["PATTERN"] <= F["pattern_keep_max"]) & \
           (ev["PI"] >= F["pi_min"]) & (ev["PI"] <= F["pi_max"]) & in_gti(ev["TIME"], std)
    src_tab = Table({c: ev[c][keep & in_src] for c in EV_COLS})
    bkg_tab = Table({c: ev[c][keep & in_bkg] for c in EV_COLS})

    def gti_tab(g):
        return Table({"START": g[:, 0], "STOP": g[:, 1]})

    flc = Table({"TIME": 0.5 * (edges[:-1] + edges[1:]), "COUNTS": fcounts.astype(np.int32),
                 "FRACEXP": bexp / Fl["bin_s"], "RATE": frate})

    meta = {
        "OBS_ID": obsid, "EXPO": expo, "SRC_CCD": src_ccd,
        "SRC_X": cx, "SRC_Y": cy, "SRC_RA": float(src_ra), "SRC_DEC": float(src_dec),
        "SRC_R": F["src_radius_arcsec"], "BKG_X": float(bx), "BKG_Y": float(by),
        "BKG_R": F["bkg_radius_arcsec"], "SRCAREA": src_area, "BKGAREA": bkg_area,
        "BACKRAT": backratio, "TSTART": float(evh["TSTART"]), "TSTOP": float(evh["TSTOP"]),
        "MJDREF": float(evh["MJDREF"]), "TIMESYS": evh["TIMESYS"], "FRMTIME": float(evh["FRMTIME"]),
    }
    hdus = [fits.PrimaryHDU()]
    for k, v in meta.items():
        hdus[0].header[k] = v
    hdus[0].header["COMMENT"] = "Retrace reduction v0 (reduction/filter/filter.py); see EXPLAIN.md"
    for name, tab in [("SRC_EVENTS", src_tab), ("BKG_EVENTS", bkg_tab), ("STDGTI", gti_tab(std)),
                      ("FLAREGTI", gti_tab(flaregti)), ("GTI", gti_tab(gti)), ("PPSGTI", gti_tab(ppsgti)),
                      ("FLARELC", flc)]:
        hdu = fits.table_to_hdu(tab)
        hdu.name = name
        hdus.append(hdu)
    outfile = OUT / f"{obsid}_{expo}_filtered.fits"
    fits.HDUList(hdus).writeto(outfile, overwrite=True)

    hashes = {name: column_hashes(tab) for name, tab in
              [("SRC_EVENTS", src_tab), ("BKG_EVENTS", bkg_tab), ("STDGTI", gti_tab(std)),
               ("FLAREGTI", gti_tab(flaregti)), ("GTI", gti_tab(gti)), ("PPSGTI", gti_tab(ppsgti))]}

    # diagnostics: image with regions, flare curve, source and scaled background curves
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.5), gridspec_kw={"width_ratios": [1, 1.6, 1.6]})
    half = 3000  # 150"
    Hm, xe, ye = np.histogram2d(X[base], Y[base], bins=300, range=[[cx - half, cx + half], [cy - half, cy + half]])
    ax[0].imshow(np.log10(Hm.T + 1), origin="lower", extent=[xe[0], xe[-1], ye[0], ye[-1]], cmap="magma")
    ax[0].add_patch(plt.Circle((cx, cy), rs, fill=False, color="lime", lw=1.5, label="source"))
    ax[0].add_patch(plt.Circle((bx, by), rb, fill=False, color="cyan", lw=1.5, label="background"))
    ax[0].invert_xaxis()
    ax[0].set_title(f"{obsid} {expo}: sky X/Y, 0.3-10 keV, PATTERN<=4 (log)")
    ax[0].legend(loc="lower left", fontsize=8)
    tt = (edges[:-1] - t0) / 1e3
    ax[1].step(tt, frate, where="mid", lw=0.7, color="k")
    ax[1].axhline(Fl["threshold_cps"], color="r", ls="--", label=f"threshold {Fl['threshold_cps']} c/s")
    for lo, hi in gti:
        ax[1].axvspan((lo - t0) / 1e3, (hi - t0) / 1e3, color="g", alpha=0.15)
    for lo, hi in ppsgti:
        ax[1].plot([(lo - t0) / 1e3, (hi - t0) / 1e3], [0.9 * np.nanmax(frate)] * 2, color="b", lw=3)
    ax[1].set_yscale("log")
    ax[1].set_xlabel(f"time since {t0:.1f} s (ks)")
    ax[1].set_ylabel("rate (c/s)")
    ax[1].set_title("flare screen: full field, PATTERN==0, 10-12 keV; green = kept; blue bar = PPS GTIs")
    ax[1].legend(fontsize=8)
    sb = (src_tab["PATTERN"] <= 4) & (src_tab["PI"] >= 300) & (src_tab["PI"] <= 10000)
    bb = (bkg_tab["PATTERN"] <= 4) & (bkg_tab["PI"] >= 300) & (bkg_tab["PI"] <= 10000)
    sc, _ = np.histogram(src_tab["TIME"][sb], bins=edges)
    bc, _ = np.histogram(bkg_tab["TIME"][bb], bins=edges)
    with np.errstate(divide="ignore", invalid="ignore"):
        ax[2].step(tt, np.where(bexp > 0, sc / bexp, np.nan), where="mid", lw=0.7, label="source region")
        ax[2].step(tt, np.where(bexp > 0, backratio * bc / bexp, np.nan), where="mid", lw=0.7,
                   label="background x area ratio")
    ax[2].set_yscale("log")
    ax[2].set_xlabel(f"time since {t0:.1f} s (ks)")
    ax[2].set_ylabel("rate (c/s), 0.3-10 keV, PATTERN<=4")
    ax[2].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / f"diag_{obsid}_{expo}.png", dpi=90)
    plt.close(fig)

    longest = float(np.max(gti[:, 1] - gti[:, 0])) if len(gti) else 0.0
    return {
        "obsid": obsid, "expo": expo,
        "file": outfile.name,
        "processed_with": str(prim.get("SASVERS", "")),
        "date_obs": str(prim.get("DATE-OBS", "")), "date_end": str(prim.get("DATE-END", "")),
        "submode": str(prim.get("SUBMODE", "")), "filter": str(prim.get("FILTER", "")),
        "ontime_s": float(evh["ONTIME"]), "livetime_s": float(evh["LIVETIME"]),
        "src_ccd": src_ccd, "src_frac_on_ccd": frac_on_ccd,
        "src_ra_deg": float(src_ra), "src_dec_deg": float(src_dec),
        "src_offset_from_RA_OBJ_arcsec": offset_obj,
        "src_rawx": float(src_rawx), "src_rawy": float(src_rawy),
        "sky_to_raw_fit_rms_pix": [rms_rx, rms_ry],
        "bkg_center_sky": [float(bx), float(by)], "bkg_src_separation_arcsec": sep_arcsec,
        "src_area_arcsec2": src_area, "src_area_good_frac": src_frac,
        "bkg_area_arcsec2": bkg_area, "bkg_area_good_frac": bkg_frac,
        "backratio": backratio,
        "stdgti_total_s": tot(std), "flaregti_total_s": tot(flaregti),
        "gti_total_s": tot(gti), "gti_n": int(len(gti)), "gti_longest_s": longest,
        "ppsgti_total_s": tot(gti_intersect(std, ppsgti)), "pps_flcutthr": pps_thr,
        "src_counts_pat4_0p3_10keV_in_gti": int(np.sum(sb & in_gti(np.asarray(src_tab["TIME"]), gti))),
        "bkg_counts_pat4_0p3_10keV_in_gti": int(np.sum(bb & in_gti(np.asarray(bkg_tab["TIME"]), gti))),
        "hashes": hashes,
    }


def main():
    P = yaml.safe_load(open(ROOT / "params.yaml"))
    OUT.mkdir(parents=True, exist_ok=True)
    summary, hashes = [], {}
    for e in P["exposures"]:
        r = process(e["obsid"], e["expo"], P)
        r["include"] = bool(e["include"])
        hashes[r["file"]] = r.pop("hashes")
        summary.append(r)
        print(f"{e['obsid']} {e['expo']}: GTI {r['gti_total_s']/1e3:.1f} ks of {r['stdgti_total_s']/1e3:.1f} ks, "
              f"longest {r['gti_longest_s']/1e3:.1f} ks, backratio {r['backratio']:.3f}, "
              f"src offset {r['src_offset_from_RA_OBJ_arcsec']:.2f}\"")
    inc = [s for s in summary if s["include"]]
    totals = {
        "included_exposures": [f"{s['obsid']}_{s['expo']}" for s in inc],
        "stdgti_total_ks": sum(s["stdgti_total_s"] for s in inc) / 1e3,
        "gti_total_ks": sum(s["gti_total_s"] for s in inc) / 1e3,
        "gti_total_livetime_corrected_ks":
            sum(s["gti_total_s"] * s["livetime_s"] / s["ontime_s"] for s in inc) / 1e3,
        "ppsgti_total_ks": sum(s["ppsgti_total_s"] for s in inc) / 1e3,
        "paper_net_pn_exposure_ks_for_comparison_only": 330,
    }
    json.dump({"totals": totals, "exposures": summary}, open(ROOT / "reduction/filter/summary.json", "w"), indent=2)
    json.dump(hashes, open(OUT / "content_hashes.json", "w"), indent=2)
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()

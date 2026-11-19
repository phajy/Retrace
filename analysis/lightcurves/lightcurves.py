#!/usr/bin/env python3
"""Stage 3 (lightcurves): binned source and background light curves per energy band.

For every included exposure, bins the cleaned source-region and background-region
events (from the filter stage) on a regular grid of `dt_s` seconds covering the
exposure's standard GTIs, in each energy band listed in params.yaml.

For each bin we record:
  SRC_<band>, BKG_<band>   raw counts in the source / background region
  FRACEXP                  fraction of the bin inside the CCD standard GTIs
  IN_FLAREGTI              fraction of the bin inside the flare-screen GTIs

Background is NOT subtracted here (the scaling factor BACKRAT is copied into the
header), and no gap filling is done: those are analysis choices for the lags stage.

Content hashes of every column of the written files go to content_hashes.json (git-tracked;
see tools/fits_hashes.py), so verifiers can compare data rather than file bytes.

Usage:  python analysis/lightcurves/lightcurves.py   (normally via `dvc repro lightcurves`)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import yaml
from astropy.io import fits
from astropy.table import Table

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.fits_hashes import file_hashes  # noqa: E402

FILT = ROOT / "reduction" / "filter" / "output"
OUT = ROOT / "analysis" / "lightcurves" / "output"
HASHES = ROOT / "analysis" / "lightcurves" / "content_hashes.json"   # git-tracked reference for verifiers


def overlap(edges: np.ndarray, gti: np.ndarray) -> np.ndarray:
    """Fraction of each bin [edges[k], edges[k+1]) covered by the GTI list."""
    cov = np.zeros(len(edges) - 1)
    lo_e, hi_e = edges[:-1], edges[1:]
    for lo, hi in gti:
        cov += np.clip(np.minimum(hi_e, hi) - np.maximum(lo_e, lo), 0, None)
    return cov / (hi_e - lo_e)


def main():
    P = yaml.safe_load(open(ROOT / "params.yaml"))
    L = P["lightcurves"]
    dt = float(L["dt_s"])
    OUT.mkdir(parents=True, exist_ok=True)
    summary, hashes = [], {}
    for e in P["exposures"]:
        if not e["include"]:
            continue
        name = f"{e['obsid']}_{e['expo']}"
        with fits.open(FILT / f"{name}_filtered.fits") as h:
            meta = dict(h[0].header)
            src = Table.read(h["SRC_EVENTS"])
            bkg = Table.read(h["BKG_EVENTS"])
            std = np.column_stack([h["STDGTI"].data["START"], h["STDGTI"].data["STOP"]])
            fgti = np.column_stack([h["FLAREGTI"].data["START"], h["FLAREGTI"].data["STOP"]])
        t0, t1 = std[:, 0].min(), std[:, 1].max()
        nb = int(np.floor((t1 - t0) / dt))
        edges = t0 + dt * np.arange(nb + 1)
        cols = {"TIME": 0.5 * (edges[:-1] + edges[1:]),
                "FRACEXP": overlap(edges, std),
                "IN_FLAREGTI": overlap(edges, fgti)}
        counts = {}
        for band, (lo, hi) in L["bands_kev"].items():
            lo_ev, hi_ev = 1000 * lo, 1000 * hi
            for reg, ev in (("SRC", src), ("BKG", bkg)):
                sel = (ev["PATTERN"] <= L["pattern_max"]) & (ev["PI"] >= lo_ev) & (ev["PI"] < hi_ev)
                c, _ = np.histogram(np.asarray(ev["TIME"][sel]), bins=edges)
                cols[f"{reg}_{band.upper()}"] = c.astype(np.int32)
                counts[f"{reg}_{band}"] = int(c.sum())
        tab = Table(cols)
        hdu = fits.table_to_hdu(tab)
        hdu.name = "LIGHTCURVE"
        for k in ("OBS_ID", "EXPO", "BACKRAT", "SRCAREA", "BKGAREA", "MJDREF", "TIMESYS"):
            hdu.header[k] = meta[k]
        hdu.header["DT"] = (dt, "bin size (s)")
        hdu.header["PATMAX"] = (L["pattern_max"], "PATTERN <= PATMAX")
        for band, (lo, hi) in L["bands_kev"].items():
            hdu.header[f"E_{band.upper()[:4]}"] = f"{lo}-{hi} keV (PI in [lo, hi) eV)"
        hdu.header["COMMENT"] = "Retrace analysis/lightcurves/lightcurves.py; counts NOT background-subtracted"
        fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(OUT / f"{name}_lc.fits", overwrite=True)
        hashes[f"{name}_lc.fits"] = file_hashes(OUT / f"{name}_lc.fits")

        # diagnostic plot: 200 s rebinned rates, background scaled to the source area
        k = 20
        m = (len(tab) // k) * k
        tt = (np.asarray(tab["TIME"][:m]).reshape(-1, k).mean(1) - t0) / 1e3
        fe = np.asarray(tab["FRACEXP"][:m]).reshape(-1, k).sum(1) * dt
        fig, ax = plt.subplots(len(L["bands_kev"]), 1, figsize=(12, 3.2 * len(L["bands_kev"])), sharex=True)
        for a, band in zip(np.atleast_1d(ax), L["bands_kev"]):
            s = np.asarray(tab[f"SRC_{band.upper()}"][:m]).reshape(-1, k).sum(1)
            b = np.asarray(tab[f"BKG_{band.upper()}"][:m]).reshape(-1, k).sum(1) * meta["BACKRAT"]
            with np.errstate(divide="ignore", invalid="ignore"):
                a.step(tt, np.where(fe > 0, s / fe, np.nan), where="mid", lw=0.7, label="source region")
                a.step(tt, np.where(fe > 0, b / fe, np.nan), where="mid", lw=0.7, label="background (scaled)")
            a.set_yscale("log")
            a.set_ylabel(f"{band} {L['bands_kev'][band]} keV (c/s)")
            a.legend(fontsize=8, loc="upper right")
        np.atleast_1d(ax)[0].set_title(f"{name}: 200 s bins, PATTERN<={L['pattern_max']}")
        np.atleast_1d(ax)[-1].set_xlabel(f"time since {t0:.1f} s (ks)")
        plt.tight_layout()
        plt.savefig(OUT / f"lc_{name}.png", dpi=90)
        plt.close(fig)

        good = np.asarray(tab["FRACEXP"]) >= 1.0
        expo_s = float(np.sum(tab["FRACEXP"]) * dt)
        summary.append({"exposure": name, "n_bins": int(len(tab)), "dt_s": dt,
                        "span_s": float(nb * dt), "exposure_s": expo_s, "bins_full_exposure": int(good.sum()),
                        "bins_partial_or_empty": int((~good).sum()), "backratio": float(meta["BACKRAT"]),
                        "counts": counts,
                        "mean_src_rate_cps": {b: counts[f"SRC_{b}"] / expo_s for b in L["bands_kev"]},
                        "mean_bkg_rate_scaled_cps": {b: counts[f"BKG_{b}"] * meta["BACKRAT"] / expo_s
                                                     for b in L["bands_kev"]}})
        print(name, json.dumps(summary[-1]["mean_src_rate_cps"]), json.dumps(summary[-1]["mean_bkg_rate_scaled_cps"]))
    json.dump({"pattern_max": L["pattern_max"], "bands_kev": L["bands_kev"], "exposures": summary},
              open(ROOT / "analysis/lightcurves/summary.json", "w"), indent=2)
    json.dump(hashes, open(HASHES, "w"), indent=2)


if __name__ == "__main__":
    main()

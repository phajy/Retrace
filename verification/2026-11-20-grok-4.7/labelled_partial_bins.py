#!/usr/bin/env python3
"""Labelled copy, not the phase-1 result.

The phase-1 code treats a bin as a gap only when its standard-GTI fraction is
below 1e-6, and it keeps the raw counts in a partly exposed bin. The lag
stage's code treats every bin with FRACEXP < 1 as a gap and interpolates it.
This script repeats the re-derivation with that second rule, so the effect of
the difference can be seen. It does not replace derive_r1_r3.py.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_r1_r3 as base

OUT = Path(__file__).resolve().parent / "outputs"


def segment_series_partial(lc, window, max_gap_s, background_subtract):
    """Same as the phase-1 series, except a bin is a gap when FRACEXP < 1."""
    i0 = window["i0"]
    i1 = i0 + window["n_bins"]
    sl = slice(i0, i1)
    frac = lc["frac"][sl]
    is_gap = frac < 1.0
    backrat = lc["backrat"] if background_subtract else 0.0
    bands = {}
    noise = {}
    gap_info = {}
    for name in ("soft", "hard"):
        src = lc[f"src_{name}"][sl].astype(float)
        bkg = lc[f"bkg_{name}"][sl].astype(float)
        net = src - backrat * bkg
        filled, n_fill, n_hold, long_gaps = base.fill_short_gaps(net, is_gap, max_gap_s, lc["dt"])
        if long_gaps:
            raise RuntimeError(f"gap longer than {max_gap_s} s in {name}: {long_gaps}")
        bands[name] = filled
        # The lag stage's noise is the mean variance of the good bins, times
        # every bin, including the interpolated ones.
        good = ~is_gap
        var = src + (backrat ** 2) * bkg
        noise[name] = float(var[good].sum() / good.sum() * var.size) if good.any() else 0.0
        gap_info[name] = {
            "filled_bins": int(n_fill),
            "held_edge_bins": int(n_hold),
            "gap_bins": int(is_gap.sum()),
        }
    return bands, noise, gap_info, int(is_gap.sum())


def main():
    repo = base.REPO
    with (repo / "params.yaml").open() as fh:
        params = yaml.safe_load(fh)
    files = {
        ("0511580101", "PNS001"): repo / "reduction/raw/0511580101/P0511580101PNS001PIEVLI0000.FTZ",
        ("0511580201", "PNS001"): repo / "reduction/raw/0511580201/P0511580201PNS001PIEVLI0000.FTZ",
        ("0511580301", "PNU002"): repo / "reduction/raw/0511580301/P0511580301PNU002PIEVLI0000.FTZ",
        ("0511580401", "PNU002"): repo / "reduction/raw/0511580401/P0511580401PNU002PIEVLI0000.FTZ",
    }
    segments, noises, notes = [], [], []
    for exp in params["exposures"]:
        if not exp["include"]:
            continue
        key = (exp["obsid"], exp["expo"])
        info, lc = base.process_exposure(files[key], params["filter"], params["lightcurves"])
        window = base.choose_window(lc, float(params["lags"]["segment_s"]))
        bands, noise, gap_info, n_gap = segment_series_partial(
            lc, window, float(params["lags"]["max_gap_fill_s"]), bool(params["lags"]["background_subtract"])
        )
        segments.append(bands)
        noises.append(noise)
        notes.append({"obsid": key[0], "expo": key[1], "gap_bins": n_gap, "gap_fill": gap_info,
                      "window_start_s": window["t_start"], "noise_soft": noise["soft"], "noise_hard": noise["hard"]})
        print(f"{key[0]} {key[1]} gap bins {n_gap} noise {noise['soft']:.6g} {noise['hard']:.6g}", flush=True)
    rows, meta = base.bin_cross_spectrum(
        segments, noises, float(params["lightcurves"]["dt_s"]), float(params["lags"]["freq_bin_factor"])
    )
    hf = base.inverse_variance_mean(rows, 7e-4, 5e-3)
    OUT.mkdir(parents=True, exist_ok=True)
    base.write_csv(OUT / "r1_lag_frequency_partial_bins.csv", rows)
    with (OUT / "r1_partial_bins_summary.json").open("w") as fh:
        json.dump({"high_frequency_mean": hf, "fourier": meta, "exposures": notes,
                   "label": "FRACEXP < 1 treated as a gap; not the phase-1 result"}, fh, indent=2)
        fh.write("\n")
    print("hf", hf["lag_s"], hf["lag_err_s"], "n", hf["n"])


if __name__ == "__main__":
    main()

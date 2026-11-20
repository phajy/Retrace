#!/usr/bin/env python3
"""Question #4 (raw vs intrinsic coherence): numbers behind the answer.

Reads analysis/lags/lag_frequency.csv (the committed R1 output) and, for every frequency bin, reports
  * the measured power divided by the Poisson noise level, in each band,
  * the raw and intrinsic coherence as stored by the lags stage,
  * the intrinsic coherence recomputed with the noise levels scaled by 0.95 and 1.05, to show how
    strongly it depends on the noise level where the power is only just above the noise.

The recomputation uses the same function as the lags stage (stingray.fourier.intrinsic_coherence).
The CSV does not store the cross spectrum, so |<C>|^2 is rebuilt as coh_raw * power_soft * power_hard.
Only |<C>| enters the coherence. At scale 1.00 this reproduces the stored values, and the script checks that.

Writes coherence_noise.json next to this script. Usage (from the repository root):
    python results/answers/issue-4/coherence_noise.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import warnings
from pathlib import Path

import numpy as np
from stingray.fourier import intrinsic_coherence

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CSV = ROOT / "analysis/lags/lag_frequency.csv"
SCALES = (1.0, 0.95, 1.05)


def intrinsic(c_abs, ps, ph, ns, nh, k):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = intrinsic_coherence(np.array([c_abs + 0j]), np.array([ps]), np.array([ph]), ns, nh, k)
    g = float(g[0])
    return None if not np.isfinite(g) else g


def main():
    raw_bytes = CSV.read_bytes()
    rows = list(csv.DictReader(l for l in raw_bytes.decode().splitlines() if not l.startswith("#")))
    out = {"source": "analysis/lags/lag_frequency.csv", "source_md5": hashlib.md5(raw_bytes).hexdigest(),
           "noise_scales": list(SCALES), "bins": []}
    for r in rows:
        v = {k: float(r[k]) for k in ("f_mean_hz", "K", "coh_raw", "power_soft", "power_hard",
                                      "noise_soft", "noise_hard")}
        stored = float(r["coh_intrinsic"]) if r["coh_intrinsic"] not in ("", "nan") else None
        c_abs = np.sqrt(v["coh_raw"] * v["power_soft"] * v["power_hard"])
        recomputed = {f"{s:.2f}": intrinsic(c_abs, v["power_soft"], v["power_hard"], s * v["noise_soft"],
                                            s * v["noise_hard"], v["K"]) for s in SCALES}
        r1 = recomputed["1.00"]
        assert (r1 is None and stored is None) or abs(r1 - stored) < 1e-3 * max(1.0, abs(stored)), \
            f"recomputation does not match the stored value at {v['f_mean_hz']} Hz"
        out["bins"].append({
            "f_mean_hz": v["f_mean_hz"], "K": int(v["K"]), "reliable": int(r["reliable"]),
            "power_over_noise_soft": v["power_soft"] / v["noise_soft"],
            "power_over_noise_hard": v["power_hard"] / v["noise_hard"],
            "defined_threshold_3_over_sqrtK": 3 / np.sqrt(v["K"]),
            "coh_raw": v["coh_raw"], "coh_intrinsic_stored": stored,
            "coh_intrinsic_err_stored": float(r["coh_intrinsic_err"]) if stored is not None else None,
            "coh_intrinsic_noise_scaled": recomputed})
    high = [b for b in out["bins"] if b["f_mean_hz"] >= 1e-2]
    out["noise_level_check_above_1e-2_Hz"] = {
        "n_bins": len(high),
        "power_over_noise_soft": [min(b["power_over_noise_soft"] for b in high),
                                  float(np.mean([b["power_over_noise_soft"] for b in high])),
                                  max(b["power_over_noise_soft"] for b in high)],
        "power_over_noise_hard": [min(b["power_over_noise_hard"] for b in high),
                                  float(np.mean([b["power_over_noise_hard"] for b in high])),
                                  max(b["power_over_noise_hard"] for b in high)],
        "note": "[min, mean, max]; the source contributes little power here, so the ratio tests the noise level"}
    json.dump(out, open(HERE / "coherence_noise.json", "w"), indent=2)

    print(f"source md5 {out['source_md5']}")
    print(f"{'f (Hz)':>9} {'K':>5} {'P/N soft':>8} {'P/N hard':>8} {'raw':>6} {'intr':>6} "
          f"{'intr 0.95N':>10} {'intr 1.05N':>10} rel")
    fmt = lambda x: f"{x:.3f}" if x is not None else "undef"
    for b in out["bins"]:
        s = b["coh_intrinsic_noise_scaled"]
        print(f"{b['f_mean_hz']:9.3g} {b['K']:5d} {b['power_over_noise_soft']:8.2f} {b['power_over_noise_hard']:8.2f} "
              f"{b['coh_raw']:6.3f} {fmt(b['coh_intrinsic_stored']):>6} {fmt(s['0.95']):>10} {fmt(s['1.05']):>10} "
              f"{b['reliable']}")
    c = out["noise_level_check_above_1e-2_Hz"]
    print("power/noise above 1e-2 Hz [min, mean, max]: soft", [round(x, 3) for x in c["power_over_noise_soft"]],
          "hard", [round(x, 3) for x in c["power_over_noise_hard"]])


if __name__ == "__main__":
    main()

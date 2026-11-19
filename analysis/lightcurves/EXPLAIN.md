# Stage 3 — lightcurves

Script: `lightcurves.py` · parameters: `exposures`, `lightcurves` · numbers: `summary.json`
· outputs: `output/<exposure>_lc.fits` and `output/lc_<exposure>.png` (DVC-tracked).

## What was done and why
For each included exposure, the source- and background-region events from the filter stage are binned
on a regular **10 s** grid (A-06) from the start of the CCD standard GTIs. Bands are **0.3–1 keV (soft)**
and **1–4 keV (hard)** (F09 Fig. 3), with PI in [lo, hi) eV. **PATTERN ≤ 4** (A-07; F09's stated selection;
Z10 says patterns were relaxed for timing, so PATTERN ≤ 12 is the first sensitivity test).

Each bin stores raw source and background counts per band, the fraction of the bin inside the standard
GTIs (`FRACEXP`) and the fraction inside the flare-screen GTIs (`IN_FLAREGTI`). The background scaling
`BACKRAT` (= 1.000) is in the header. **No background subtraction, gap filling or segment selection
happens here.** Those are lag-stage choices, kept separate so they can be varied without rebinning.

## Results (from `summary.json`; whole exposures)
| Exposure | Exposure (ks) | Soft src (c/s) | Soft bkg, scaled (c/s) | Hard src (c/s) | Hard bkg, scaled (c/s) |
|---|---|---|---|---|---|
| 0101 PNS001 | 121.5 | 2.54 | 0.022 | 0.54 | 0.014 |
| 0201 PNS001 | 102.1 | 3.83 | 0.032 | 0.87 | 0.022 |
| 0301 PNU002 | 104.0 | 3.48 | 0.030 | 0.70 | 0.025 |
| 0401 PNU002 | 101.8 | 2.87 | 0.032 | 0.53 | 0.039 |

Averaged over each exposure (flares included), the background is ~1% of the source in the soft band and 2.5–7.5% in the hard band.

## Checks run
* Count totals per band are recorded in `summary.json` (e.g. 0101: 309,154 soft and 65,652 hard source counts).
* The plots `output/lc_*.png` were generated (200 s bins, source vs scaled background per band) for visual inspection.

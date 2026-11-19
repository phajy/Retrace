# Stage 2 — filter (event selection, regions, flare GTIs) — reduction v0

Script: `filter.py` · parameters: `params.yaml` → `exposures`, `filter` · numbers: `summary.json`
· outputs: `output/` (DVC-tracked): one `<ObsID>_<expo>_filtered.fits` per exposure and
`diag_*.png` · column hashes: `content_hashes.json` (in git).

## What was done and why
1. **Source position.** Iterative centroid (20″ radius) of 0.3–10 keV, PATTERN ≤ 4, FLAG == 0
   events, starting at the header RA_OBJ/DEC_OBJ (A-03). Result: 0.7–1.9″ from RA_OBJ in all exposures,
   all source-region events on CCD 4, at RAWX ≈ 37, RAWY ≈ 190–191. The Large Window active rows are RAWY 103–199,
   so the 35″ (8.5 pixel) circle just fits inside the chip.
2. **Source region.** 35″ circle (paper).
3. **Background region** (A-04). 35″ circle on CCD 4 at the same RAWY as the source (same distance
   from the readout node, K13), centred 25 RAWX pixels away (103″). Sky↔RAW positions use an affine
   fit to the events on CCD 4. Fit residual ≈ 0.29–0.32 pixel, consistent with pixel quantisation (1/√12 = 0.29).
4. **Effective areas.** A 0.5″ grid in each circle is mapped to RAW pixels and looked up in a mask of
   pixels that recorded FLAG == 0 events. Both circles are fully on good pixels:
   3848.45 arcsec² each, so `BACKRAT` (background → source scaling) = 1.000.
5. **Flare screen** (A-05). Full-field PATTERN == 0, 10–12 keV, FLAG == 0 rate in 100 s bins; bins
   below 0.4 c/s are kept. These flare GTIs are stored with the CCD standard GTIs, their
   intersection, and the PPS's own optimised GTIs. **Events are not cut by the flare GTIs here.** The
   choice is made downstream (see `analysis/lags/EXPLAIN.md`).
6. **Kept events:** FLAG == 0, PATTERN ≤ 12, PI 200–12000 eV, inside the CCD-4 standard GTIs. The timing
   pattern cut (PATTERN ≤ 4) is applied in the light-curve stage so it can be varied (A-07).

## Results (from `summary.json`)
| Exposure | Std GTI (ks) | After flare screen (ks) | Longest clean stretch (ks) | Src counts* | Bkg counts* |
|---|---|---|---|---|---|
| 0101 PNS001 | 121.5 | 110.3 | 35.1 | 347,737 | 3,702 |
| 0201 PNS001 | 102.1 | 76.3 | 10.3 | 363,674 | 3,489 |
| 0201 PNU027 (excluded, A-01) | 3.3 | 1.2 | 0.7 | 4,270 | 44 |
| 0301 PNU002 | 104.0 | 68.6 | 7.6 | 285,091 | 2,740 |
| 0401 PNU002 | 101.8 | 73.4 | 24.5 | 247,625 | 2,451 |

\* 0.3–10 keV, PATTERN ≤ 4, inside the flare-screened GTIs.

Totals for the four included exposures: 429.4 ks standard GTI; **328.6 ks after the flare screen**
(303.9 ks after scaling by LIVETIME/ONTIME). F09 quotes 330 ks net pn exposure. **Comparison only:** the
0.4 c/s threshold was set from the SAS-thread recipe before this number was seen, and we don't know
which definition of "net exposure" F09 used. So the near-agreement is not evidence that our screen
matches theirs. The PPS optimised screen (SAS 18; thresholds 3.9–4.6 c/s on a 0.5–7.5 keV
source-excluded rate) removes nothing.

**Consequence for timing:** after the 0.4 c/s screen no orbit keeps a clean stretch longer than 35 ks
(as short as 7.6 ks in 0301). This can't give the ~1e-5 Hz frequencies in F09 Fig. 3, or the
"4 segments of about 100 ks" in Z10. That is why the timing baseline uses whole-orbit segments with
background subtraction (A-09).

## Checks run
* The source is single-CCD: 100% of the source-circle events are on CCD 4 in every exposure.
* Sky↔RAW map residuals are at the quantisation level (above).
* Diagnostic plots inspected by eye (`output/diag_*.png`). Neither region contains a visible
  point source. The background circle lies off the out-of-time streak and clear of the chip gap.
  The source-region light curve is 1–2 orders of magnitude above the scaled background, except in the
  strongest flares (end of orbit 0301, up to ~1 c/s in 0.3–10 keV).
* Content hashes (sha256 of each data column, canonical big-endian; `tools/fits_hashes.py`) of every
  binary table in the written files go to `content_hashes.json`, which is git-tracked so a verifier on a
  fresh clone has a reference to compare FITS products by content, not file bytes. (Until 2026-11-19 this
  file sat inside the DVC-tracked `output/` folder, where a fresh clone could not see it; see `docs/LOG.md`.)

## Known limitations
* Not reprocessed with SAS; no check of the PPS calibration against SAS 8 (M-01).
* The good-pixel mask is "pixels with any FLAG == 0 event". It is coarse but adequate given both circles are fully on chip.
* Some source PSF-wing light reaches the background circle (103″ away, on a PSF spoke path).
  This is harmless for lags (see A-04) but would matter for spectra.
* EPIC-pn counting-mode intervals during strong flares are not separately identified (they fall in
  flaring periods; the standard GTIs exclude most of them).

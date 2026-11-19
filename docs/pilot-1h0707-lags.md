# Pilot: lag–frequency spectrum of 1H 0707–495 (Fabian et al. 2009, Fig. 3)

## Target
- Fabian, Zoghbi, Ross, Uttley, Gallo, Brandt, ..., Young 2009, Nature 459, 540.
  arXiv:0905.4383. "Broad line emission from iron K- and L-shell transitions in the active galaxy 1H0707-495".
- Fig. 3: lag versus frequency between 0.3–1 keV (soft, reflection-dominated) and 1–4 keV
  (hard, power-law-dominated).
- Published result: the soft band follows the hard band by ~30 s at frequencies above
  ~0.6–0.7 mHz (main text: "faster than 0.6 mHz"; Fig. 3 caption: above 7e-4 Hz). At low
  frequencies the lag has the opposite sign (hard lags soft). Match the sign convention of Fig. 3,
  where the high-frequency soft lag is negative, and state the convention in every output.
- Supplementary Information: mean high-frequency lag (> 7e-4 Hz) between 0.5–1 and 3–7 keV is
  −6 ± 18 s. Band choice matters; this is a natural first check request.

## Data (XMM-Newton EPIC-pn, Large Window mode, four consecutive orbits from 2008-01-29)
| ObsID | Start (UT) | Duration | PPS pn calibrated event list (size, compressed) |
|---|---|---|---|
| 0511580101 | 2008-01-29 18:28 | ~124 ks | P0511580101PNS001PIEVLI0000.FTZ (212 MB) |
| 0511580201 | 2008-01-31 16:29 | ~124 ks | P0511580201PNS001PIEVLI0000.FTZ (206 MB); also a short PNU027 exposure (26.5 MB) — decide and document whether to include |
| 0511580301 | 2008-02-02 18:22 | ~123 ks | P0511580301PNU002PIEVLI0000.FTZ (226 MB) |
| 0511580401 | 2008-02-04 18:24 | ~122 ks | P0511580401PNU002PIEVLI0000.FTZ (245 MB) |

- URLs: `https://nasa-heasarc.s3.amazonaws.com/xmm/data/rev0/<ObsID>/PPS/<file>` (anonymous access).
  The PPS directories also hold pn flare-background time series (`...FBKTSR0000.FTZ`).
- Whole observation on HEASARC: ~1.1–1.3 GB per ObsID (ODF ~0.3 GB, PPS ~0.8–0.9 GB).
  Measured 2026-11-19 from the S3 listing.
- ObsIDs confirmed from Kara et al. 2013 (arXiv:1210.1465), Table 1.

## What the paper specifies
- SAS v8.0.0; PATTERN <= 4; source circle radius 35 arcsec; background from the same chip;
  flare-filtered; 330 ks net pn exposure.

## What the paper does NOT specify (record as ASSUMPTIONS, test sensitivity)
- Light-curve bin size, segment length, frequency binning, background subtraction for timing,
  flare-filtering threshold, treatment of gaps.
- Sources for sensible choices:
  - Zoghbi et al. 2010, MNRAS (arXiv:0910.0367) — the detailed follow-up on the same data.
  - Kara et al. 2013 (arXiv:1210.1465) — 10 s bins; cross-spectral lags following Nowak et al. 1999;
    coherence and errors following Vaughan & Nowak 1997; frequencies up to 0.01 Hz;
    Timmer & König 1995 simulations to test biases.

## Plan
- **Reduction v0:** PPS calibrated event lists, filtered in Python with astropy (PATTERN, FLAG,
  energy, source/background regions, flare GTIs). No SAS needed.
- **Reduction v1 (later):** reprocess the ODFs with SAS in a container; compare with v0.

Stages (DVC):
1. `fetch`   — `dvc import-url` the four PPS pn event lists (and flare time series).
2. `filter`  — event selection + flare filtering → cleaned events + GTIs (EXPLAIN.md).
3. `lightcurves` — source and background light curves in 0.3–1 and 1–4 keV on common GTIs.
4. `lags`    — averaged cross-spectrum (Stingray), lag vs frequency with errors and coherence.
5. `compare` — compare with Fig. 3 of Fabian et al. 2009. Use digitised points from the figure,
   stating that they are digitised. Report agreement or disagreement plainly.
6. `report`  — summary page: what was reproduced, what wasn't, assumptions, sensitivity tests.

Then a fresh session (the verifier) re-runs everything from a clean clone and writes
`verification/REPORT.md`.

## Extensions (after the pilot)
- Band choice (0.5–1 vs 3–7 keV, per the Supplementary Information).
- Kara et al. 2013: 14 observations, 1.3 Ms; lag–frequency and lag–energy spectra.
- Reverberation modelling with kerrz/Gradus impulse responses.

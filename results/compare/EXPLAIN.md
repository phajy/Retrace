# Stage 5: compare (R1 against the digitised F09 Fig. 3)

Plan, with criteria fixed in advance: [`PLAN.md`](PLAN.md) (commit `13438ec`, with Amendment 1 of 2026-11-20, also
made before digitising). Digitising rules: [`DIGITISE.md`](DIGITISE.md).
Code: `compare.py` · tests: `test_compare.py` · calibration (no F09 value): `calibration.json` · outputs (once the
digitisations exist): `comparison.json`, `comparison.csv`, `digitised_combined.csv`, `comparison.png`.

**Status (2026-11-20): code written and tested on made-up input; our own spread measured on our own bins. No point of
F09 Fig. 3 has been digitised, and there are no digitised values in the repository.** Two DVC stages:
`compare_calibration` runs now, and `compare` is in `dvc.yaml` but commented out until both digitisations are
committed.

## What the code does
1. **Self-checks (every run).**
   * Our values on any bin come from `lags.bin_spectra`, the function that made R1, applied to the Fourier
     frequencies inside that bin. Re-binning on the lags stage's own bins this way must reproduce `lags.bin_spectra`
     exactly and `analysis/lags/lag_frequency.csv` to its printed precision.
   * Rebuilding the baseline segments from the light curves (`segmented_spectrum`, which uses the lags stage's
     functions step by step) must reproduce `unbinned_cross_spectrum.npz` exactly, and the noise levels in the CSV.
   * The stage stops if either fails.
2. **Two digitisations** are read from `digitised/<id>/`, matched, checked for agreement and combined, as in
   PLAN.md step 4.
3. **F09's bins** (A-15), **our lags on them** and the **per-bin statistics** (z_F, z_C, ρ), as in PLAN.md step 5.
4. **Summary numbers:** the sign change, the high-frequency weighted means and **z_mean** (Amendment 1).
5. **Our own spread** (Amendment 1, A-19):
   * the 8 reference variants are evaluated on F09's bins, with z = (ours − variant) / variant's error;
   * the rms and |z| limits are the largest values among them;
   * F09's rms z_F and largest |z_F| are compared with those limits.
6. **Two outcomes:** under the amended rule, and under the original rule (13438ec).
7. **Sensitivity variants:** points 3–6 again, for edges shifted by ±¼ bin and for each digitisation on its own.

`python results/compare/compare.py --calibrate` (the `compare_calibration` stage) does point 5 on our own baseline
bins instead of F09's. It also runs larger variants that are not reference variants, and writes
`calibration.json`. It needs no digitised value.

## Choices the plan left to the code
Decided while writing the code, before any digitised values existed.
* **Matching points:** mutual nearest neighbours in log frequency, closer than half the smallest spacing between
  points in either digitisation. When both digitisers found the same points, this is the same as matching in order.
* **Points found by one digitiser only** are not compared. Their frequency is still used for the bin edges, so a
  missed point does not widen its neighbours' bins.
* **An error-bar end recorded by one digitiser only:** F09's error S is then undefined, and the bin is not compared
  (status "no complete error bar").
* **The code stops** if the figure has more than one data series, or if horizontal error bars are recorded for some
  points and not others. Both need a decision and a new commit of the plan.
* **Midpoint edges:** the outer edges of the first and last bins are extrapolated with the spacing to the
  neighbouring point. The ±¼-bin sensitivity variant shifts all edges by ¼ of the median bin width in log frequency.
* **Noise levels** for the intrinsic coherence, and so for the reliability flag, are read from `lag_frequency.csv`,
  which prints them to 6 significant figures. The segmentation variants use their own noise levels at full precision.
* **Sign change:** the positive-to-negative crossings among the bins that count, found as in `lags.py`. "Adjacent
  pair" is counted in positions among those bins. If either spectrum does not have exactly one crossing, the
  criterion cannot be applied. The outcome can then still be "agrees, with differences" or "does not agree" from the
  other criteria, but not "agrees"; otherwise it is "not covered by the plan".
* **Weighted means** over 7×10⁻⁴–5×10⁻³ Hz select bins by F09's point frequency. F09's points are weighted by 1/S².
* **δ_m**, the digitisation uncertainty of F09's weighted mean: the 1/S²-weighted mean of the points' δ, as if the
  digitisation errors of all points were fully correlated. This is the larger of the two simple choices (fully
  correlated or independent), so it does not understate the uncertainty.
* **z for a reference variant** is (ours − variant) divided by the variant's own error, with no digitisation term:
  the variant plays the part of another analysis, as F09 does in z_F.
* **The limits** are the largest rms and the largest |z| over the reference variants, not a percentile. With 8
  variants, a percentile would mean little.
* **A bin where a variant has no Fourier frequency** is left out of that variant's rms and largest |z|.
* **The reference edge shifts** apply to edges from horizontal bars too. Those edges are also read from a printed
  figure, and the shifts also stand in for a Fourier grid that is placed differently. The pre-registered ±¼-bin
  sensitivity variant still applies to midpoint edges only, as PLAN.md says.
* **"100 ks window at the end of the usable stretch":** the stretch is the run of usable bins (fully exposed, or a
  gap of 200 s or less, as in `lags.choose_segments`) that holds the window the lags stage picks. The window is
  moved to its end.
* **The segmentation variants** are built in `compare.py` from the light curves rather than by changing `lags.py`.
  The lags stage, and R1, are left untouched. The baseline self-check guards against the two codes drifting apart.
* **Agreement check** for a point without a complete error bar: only the frequency part can be applied.
* **δ floor** for the combined points: 0.5% of the mean of the two digitisers' plotted lag-axis ranges.
* **One digitisation on its own** (sensitivity variant): δ is the floor, 0.5% of that digitiser's lag-axis range.

## Our own spread on our own bins (`calibration.json`)
On the 9 reliable bins of our baseline (factor 1.4), the reference variants give rms z of 0.26–0.57 and largest |z|
of 0.42–1.05. These numbers, and those of the larger variants, are tabulated in
[PLAN.md, Amendment 1](PLAN.md#amendment-1-2026-11-20-why-the-outcome-rule-changed). Over every variant, the
high-frequency weighted mean moves by at most 0.53 of its error (0.39 for the reference variants), and the sign
change stays between 5.6×10⁻⁴ and 6.4×10⁻⁴ Hz. On the made-up 1.6× bins of the tests, the limits are 0.47 (rms) and
0.81 (|z|). The limits used in the real comparison are recomputed on F09's bins.
Provenance: `calibration.json` md5 `8e813ae73131877345294405b9ee50ab`; `test/test_results.json` md5
`69265cabe16168fa710a2af2fbefe913`.

Before Amendment 1, the same measurement was first run as a scratch script outside the repository. That script gave
the same picture, with z divided by the baseline error instead of the variant's error. It was not kept: the stage
replaces it.

## Tests (`test_compare.py`; made-up input only)
The made-up "published" points are our own baseline lags on geometric bins with a factor of 1.6 (neither 1.4 nor
2.4), with error bars equal to ours. Two made-up "digitisations" add reading errors of 0.05 of the error bar in lag
and 0.002 dex in frequency. No value from F09 is used. Result: **all 58 checks passed** (`test/test_results.json`):
* **identical points:**
  * "agrees" under both rules;
  * both self-checks pass;
  * all 8 reference variants run;
  * the points are within our spread (rms z_F 0.06, largest 0.13), and |z_mean| = 0.10;
  * the A-11 side result recovers the spacing (1.5999), and every point passes the agreement check;
  * error bars "similar" (median ρ 0.998), and each digitisation alone also "agrees";
* **edge inference:** without reading errors, the midpoint rule recovers the true bin edges exactly;
* **horizontal error bars:** used as edges when present → "agrees", and the reference edge shifts run on them;
* **one low-frequency bin moved beyond our spread** (by the |z| limit plus one error bar) → "agrees, with
  differences", naming that bin; the high-frequency mean is unaffected. Demonstration run in `test/demo/`;
* **the high-frequency points moved together** so that z_mean ≈ 1.5 → "agrees, with differences"; so that
  z_mean ≈ 3 → "does not agree". The high-frequency mean is named in the reasons in both cases;
* **one bin with opposite signs**, both more than 2σ from zero → "does not agree", naming that bin;
* **the two digitisations differ by 0.6 error bars at one point:**
  * only that point fails the agreement check;
  * its δ is half the difference or the floor, whichever is larger;
  * the outcome is still "agrees";
* **one digitiser misses a point:** it is listed as unmatched, its bin is not compared, and the outcome is still
  "agrees";
* **the code stops** for two data series and for a single digitisation;
* **the amended rule on its own,** with hand-made inputs, in 14 cases: all four outcomes; z_mean either side of 1
  and 2; opposite signs; a distant sign change and an undetermined one; a missing weighted mean, spread or bin.
  **The original rule** on its 8 cases from the first version.

The outcome under each rule is recorded for every scenario in `test_results.json`.

History of the tests:
* In the first version (before Amendment 1), two tests failed on the first run and were fixed in the tests, not in
  `compare.py`.
  * **δ check:** it had ignored the floor. In that bin the 3 s floor is larger than half the difference, and the
    code was right to use it.
  * **Edge shifts:** the test expected the edge-shift variants to "agree" as well. They don't, which led to the
    finding below and to Amendment 1.
* The reworked tests passed on their first run. Before that run, one rule in `classify` was changed: a missing own
  spread now gives "not covered by the plan" instead of "agrees, with differences". After it, the label in the
  lower panel of the figure was changed for test runs, to read "made-up points" instead of "F09 points".

## Finding that led to Amendment 1
Our own spectrum compared with itself, using exact made-up points on the true 1.6× bins (S = our error, δ = 3 s),
after shifting all bin edges by a fraction of a bin width. This is a measurement, not a test (`test/test_results.json`):

| Edge shift (fraction of a bin) | ±0.05 | ±0.10 | ±0.25 |
|---|---|---|---|
| Largest \|z_F\| over the 7 bins that count | 0.51, 0.55 | 0.66, 0.81 | 1.45, 1.68 |
| z_mean | +0.18, −0.15 | +0.30, +0.09 | −0.02, +0.46 |
| Outcome under the original plan | agrees | agrees | agrees, with differences |
| Outcome under Amendment 1 | agrees | agrees | agrees, with differences |

Moving the edges swaps some Fourier frequencies between neighbouring bins. The lag at a single frequency scatters
widely, so the bin average moves by a sizeable fraction of its error. On our own 1.4× bins the effect is larger
(the calibration above), and other segmentations do much the same. A quarter-bin shift is outside the reference
variants, so it still gives "agrees, with differences" under the amended rule. That is reported as a sensitivity
result.

## Stage definitions
In `dvc.yaml`:
* **`compare_calibration`** runs now. Its dependencies are `compare.py`, `lags.py` (for `bin_spectra` and the
  segment functions), the lags outputs, the light curves and `params.yaml` (`exposures`, `lightcurves`, `lags`). It
  writes `calibration.json`.
* **`compare`** is commented out until both digitisations are committed. It runs the tests, then the comparison,
  with the same dependencies plus `test_compare.py` and `digitised/`.

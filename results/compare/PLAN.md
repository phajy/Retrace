# Comparison of R1 with Fabian et al. 2009, Fig. 3: plan, fixed before digitising

Result: **R1** (lag–frequency spectrum, 0.3–1 keV vs 1–4 keV). Check: **Compared**, as defined in
[`docs/METHODOLOGY.md`](../../docs/METHODOLOGY.md#levels-of-checking). Plan written by the explainer
(Claude Opus 5.5 in Claude Code) on 2026-11-20, before any point of F09 Fig. 3 has been digitised. The commit
that adds this file is the reference version. Any later change to it is made in a new commit with the reason
recorded in [`docs/LOG.md`](../../docs/LOG.md), and the outcome under this version is still reported.

F09 = Fabian et al. 2009, *Nature* 459, 540 (arXiv:0905.4383).

## What is compared, and what is not used
* **Our side:** the cross spectrum of the current baseline (`analysis/lags/output/unbinned_cross_spectrum.npz`),
  re-binned onto F09's frequency bins. Lags, errors (A-12) and the reliability flag (A-13) are computed exactly
  as in `analysis/lags/lags.py`; only the bin edges differ.
* **F09's side:** the points of Fig. 3, digitised independently by two digitisers ([`DIGITISE.md`](DIGITISE.md)).
* **Published values are never inputs to our analysis.** Only the digitised *frequencies* of F09's points are
  used, to define the bins on which both spectra are compared. They describe F09's method (where it evaluated
  the lag), not its result. The digitised lags and error bars are used only in the statistics below.
* No recollection of the maintainer (an F09 co-author) about how Fig. 3 was made is used. If one comes up
  during digitisation, it is written down as an "AY" item in `docs/assumptions.md` and kept out of this comparison.

## Order of work
1. Commit this plan and `DIGITISE.md`.
2. The explainer writes the comparison code (`results/compare/compare.py`, a DVC stage `compare`) and tests it
   on made-up input in the digitised format (our own points with noise added, never F09 values). It is committed
   **before** any digitised values are in the repository. The explainer does not look at Fig. 3 points until then.
3. Two independent digitisations, each committed on its own (see [`DIGITISE.md`](DIGITISE.md) for the rules):
   * **AY:** Andy Young with WebPlotDigitizer. Not blind: he has seen our result.
   * **AI:** an AI agent in Cursor, working in a clean clone of a commit that has no digitised values (from
     step 1 or 2). It is told not to open our results, so it is blind to them, and AY's file is not in that commit.
     Its prompt is drafted by the explainer and quoted word for word in its notes.
   Both read the arXiv version of the figure (A-17).
   Neither digitiser looks at the other's values before their own are saved.
4. Check that the two digitisations agree (below) and combine them.
5. Run the `compare` stage. Results go on a result page in this folder, on the R1 page and in the score sheet.

## Step 4: combining the two digitisations
* **Matching points.** Points are matched in order of frequency. If the two digitisers found different numbers of
  points, both look again at the unmatched ones and record what they see. Only points found by both are compared;
  the rest are listed.
* **Agreement check** (a quality check, not a filter). The two readings of a point agree if their lags differ by
  less than 0.25 of F09's error bar for that point and their frequencies by less than 0.02 dex. Points that fail
  are looked at again by both digitisers. Whatever difference remains is kept.
* **Combined value:** the mean of the two readings, for every quantity (frequency, lag, error-bar ends).
  Neither reading is ever preferred, and never because it agrees better with our result.
* **Digitisation uncertainty** of a lag, δ: half the difference between the two readings, with a floor of 0.5%
  of the plotted lag-axis range (a typical precision for placing a point on a printed figure; A-18). Error-bar ends
  are treated the same way.
* **F09's error,** S: half the length of the combined vertical error bar. Asymmetry is recorded and reported.
  The bars are taken to be ±1σ unless the paper says otherwise (A-16).

## Step 5: F09's frequency bins (A-15)
* If Fig. 3 has horizontal error bars, their ends are taken as F09's bin edges.
* Otherwise the edges are the geometric midpoints between consecutive points. The first and last edges are
  extrapolated with the mean spacing of the neighbouring points.
* An F09 bin that contains none of our Fourier frequencies (spacing 1×10⁻⁵ Hz, from 1×10⁻⁵ Hz) is not compared.
* **Side result for A-11.** The spacing of F09's points is fitted with a constant ratio. The ratio and the scatter
  about it are reported. If the ratio is clear, A-11 is updated in a separate commit with the reason "read from
  the frequencies of F09's points", and the baseline is re-run. That change cannot affect this comparison,
  which uses F09's bins in either case.

## Step 5: statistics, for each compared bin j
With τ ± σ our lag and error on F09's bin, T the combined digitised F09 lag, S its error and δ the digitisation
uncertainty:
* d = τ − T
* **z_F = d / √(S² + δ²)**: the difference in units of F09's own error bar. **This is the main statistic.**
  Both analyses use the same photons, so a faithful reproduction should differ from F09 by much less than
  F09's error. A combined error (σ and S added in quadrature) would be too lenient, for the same reason as in
  check request #1.
* z_C = d / √(σ² + S² + δ²): the usual combined-error difference. Reported for completeness only. χ² = Σ z_C²
  and its probability for the number of bins are also reported.
* ρ = σ / S: the ratio of the error bars. This tests A-12 (how errors are computed) and K, not the lags.

Summary numbers, computed the same way for both spectra on F09's bins:
* the frequency where the lag changes sign (log-linear interpolation, as in `lags.py`), and which pair of bins it
  falls between;
* the weighted mean lag over the bins with frequency in [7×10⁻⁴, 5×10⁻³) Hz (the A-14 range), with F09's
  errors as the weights for F09's points.

**Which bins count.** The outcome below uses the compared bins where our re-binned value is reliable (A-13; this
depends on our data only, not on F09's). All other bins are shown in the table and the figure, with their
z values, but do not decide the outcome.

## Outcomes, decided now
For the R1 "Compared" entry in the score sheet:
* **Agrees with F09 Fig. 3:** |z_F| ≤ 1 in every bin that counts, and the sign change falls between the same
  pair of bins, or an adjacent pair.
* **Agrees, with differences:** every |z_F| ≤ 2, and at least one is between 1 and 2. Each such bin is listed.
* **Does not agree:** any of
  * a bin with |z_F| > 2;
  * a bin where the two lags have opposite signs and each is more than 2σ from zero (σ for ours, S for F09's);
  * a sign change more than one bin away from F09's.

Separately, the error bars are called **similar** if the median ρ is between 0.67 and 1.5. Otherwise they
**differ**, and A-12 is the first thing to look at. This does not change the outcome above.

Whatever the outcome, the baseline does not change because of it. Differences may be explored only with
the sensitivity tests already in [`docs/assumptions.md`](../../docs/assumptions.md) (for example PATTERN ≤ 12,
A-07). Those are reported next to the baseline comparison and never replace it.

## Sensitivity of the comparison itself, reported alongside
* Bin edges shifted by ±¼ of a bin width (in log frequency), when the edges come from midpoints rather than
  horizontal error bars.
* Each digitisation on its own instead of their mean (A-18).

If either changes the outcome, that is stated next to it.

## What this check will and will not show
* It shows whether our baseline agrees with Fig. 3 as published, bin by bin, within the stated assumptions.
* It does not show which assumption causes a difference, if there is one.
* It does not make R1 a reproduction on its own. A re-derivation (new code from the written method) is a separate check.
* The comparison code is written by the explainer, who also wrote R1. The safeguards are that this plan and the
  code are committed before the digitised values exist, that the digitisations are by others, and that a verifier
  can re-run the stage.

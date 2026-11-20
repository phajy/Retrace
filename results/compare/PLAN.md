# Comparison of R1 with Fabian et al. 2009, Fig. 3: plan, fixed before digitising and amended before the comparison was run

Result: **R1** (lag–frequency spectrum, 0.3–1 keV vs 1–4 keV). Check: **Compared**, as defined in
[`docs/METHODOLOGY.md`](../../docs/METHODOLOGY.md#levels-of-checking). Plan written by the explainer
(Claude Opus 5.5 in Claude Code) on 2026-11-20, before any point of F09 Fig. 3 has been digitised. The commit
that adds this file is the reference version. Any later change to it is made in a new commit with the reason
recorded in [`docs/LOG.md`](../../docs/LOG.md), and the outcome under this version is still reported.

**Amendment 1 (2026-11-20), made before the comparison was run, but after both digitisations had been committed**
(see [what actually happened](#what-actually-happened)). The explainer proposed it without having seen any digitised
value. The maintainer approved it after making his own digitisation, having seen our result. The reference version
is commit `13438ec`. Amendment 1 changes how the outcome is decided, for the reason given in
[its own section](#amendment-1-2026-11-20-why-the-outcome-rule-changed). The outcome under the original rule is still
computed and reported next to the amended one. Everything else (what is compared, the digitisations, the bins, the
statistics per bin, the sensitivity variants) is unchanged.

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
   Amendment 1 and the `compare_calibration` stage (our own spread on our own bins, no F09 value) were meant to be
   committed at this step too. In fact the digitisations came first ([what actually happened](#what-actually-happened)).
3. Two independent digitisations, each committed on its own (see [`DIGITISE.md`](DIGITISE.md) for the rules):
   * **AY:** Andy Young with WebPlotDigitizer. Not blind: he has seen our result.
   * **AI:** an AI agent in Cursor, working in a clean clone of a commit that has no digitised values (from
     step 1 or 2, preferably the commit with Amendment 1). It is told not to open our results, so it is blind to
     them, and AY's file is not in that commit.
     Its prompt is drafted by the explainer and quoted word for word in its notes.
   Both read the arXiv version of the figure (A-17).
   Neither digitiser looks at the other's values before their own are saved.
4. Check that the two digitisations agree (below) and combine them.
5. Run the `compare` stage. Results go on a result page in this folder, on the R1 page and in the score sheet.

## What actually happened
Recorded on 2026-11-20, when the digitisations were received. Times are git commit times (UTC). Steps 2 and 3 took
place in the opposite order, and the AI digitisation was not done as step 3 describes.
* **09:58:** this plan and `DIGITISE.md` committed (`13438ec`), as in step 1.
* **10:10:** the AI digitisation (Grok 4.7 High Fast in Cursor, 10:04–10:10) committed on
  `digitise/ai-grok-4.7-2026-11-20` (`7f0853a`), from `13438ec`. It departed from step 3 in three ways, all stated in
  its own notes:
  * **It was not blind.** It worked in the Cursor workspace where it had re-run the pipeline on 2026-11-19 (the
    R1/R3 verification), and it had read the R1 page and our lag table then.
  * **It did not start from a clean clone.**
  * **It did not get the drafted prompt.** Its prompt was one line asking it to follow `DIGITISE.md`.

  What limits the effect: it read the coordinates from the PDF's drawing commands with a script that is committed
  (`extract_fig3.py`). The reading involves no judgement by eye and can be repeated from the PDF, whose SHA-256 is
  recorded.
* **10:54:** AY's digitisation (WebPlotDigitizer, by hand on a screen grab, 10:15–10:45) committed on `digitise/ay`
  (`95d1a75`), from `13438ec`. AY had seen our result. He states that he had not seen the AI's values.
* **13:45:** the comparison code, its tests, the `compare_calibration` stage and Amendment 1 committed (`6426985`).
  * **The explainer had not seen any digitised value.** The digitise branches first reached the explainer's checkout
    at 14:12 UTC, through a pull recorded in the git reflog.
  * **The maintainer approved Amendment 1 after making his digitisation,** having seen our result. Whether he had
    compared his points with R1 by then is not recorded.
* **Wrong statements, now corrected:** the commit message of `6426985` said Amendment 1 was made before any point was
  digitised. So did, until this correction, this plan, `EXPLAIN.md`, A-19, the README and the R1 page. That was wrong.
* **Step 4:** the agreement check was then run on the two digitisations. All 12 points match, and none fails the
  check: the largest differences are 0.35 s in lag (0.05 of F09's error bar) and 0.003 dex in frequency.
* The outcome under the original rule (13438ec), whose plan did come before any digitising, is reported next to the
  amended outcome.

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
* *(Amendment 1)* **z_mean = (m_ours − m_F09) / √(e_F09² + δ_m²)**, where m are the two weighted means, e_F09 is the
  error of F09's weighted mean and δ_m is the digitisation uncertainty of F09's mean, taken as the weighted mean of
  the δ of its points (fully correlated between points). As for z_F, our own error is not added, because the
  photons are shared.

**Our own spread** *(Amendment 1; A-19)*. The same comparison is made between our baseline and **reference
variants** of our own analysis: other choices that F09 does not state or that cannot be read from Fig. 3. For each
variant, z = (ours − variant) / (variant's error) in each bin that counts, the analogue of z_F with no digitisation
term. The reference variants are fixed now:
* all bin edges moved by −0.10, −0.05, +0.05 and +0.10 of the median bin width (in log frequency). This applies
  to edges from horizontal bars as well as from midpoints;
* one window of 95, 90 or 80 ks per orbit instead of 100 ks, placed by the A-09 rule;
* the 100 ks window placed at the end of each orbit's usable stretch instead of where A-09 puts it.

On F09's bins, the **rms limit** is the largest rms of z over the bins that count among the reference variants, and
the **|z| limit** is the largest single |z| among them. F09's points are **within our own spread** if the rms of
z_F over the bins that count is no larger than the rms limit and no |z_F| is larger than the |z| limit.

**Which bins count.** The outcome below uses the compared bins where our re-binned value is reliable (A-13; this
depends on our data only, not on F09's). All other bins are shown in the table and the figure, with their
z values, but do not decide the outcome.

## Outcomes (Amendment 1), decided before the comparison was run
For the R1 "Compared" entry in the score sheet:
* **Agrees with F09 Fig. 3:** all of
  * |z_mean| ≤ 1;
  * the sign change falls between the same pair of bins, or an adjacent pair;
  * F09's points are within our own spread.
* **Does not agree:** any of
  * |z_mean| > 2;
  * a bin where the two lags have opposite signs and each is more than 2σ from zero (σ for ours, S for F09's);
  * a sign change more than one bin away from F09's.
* **Agrees, with differences:** neither of the above, with 1 < |z_mean| ≤ 2 or F09's points outside our own spread
  (or both). Each reason is stated, and the bins with |z_F| above the |z| limit are listed.
* **Not covered by the plan:** none of the criteria for a difference is met, but one criterion for "agrees" cannot
  be applied (the sign change is not a single crossing in both spectra, the weighted mean has no bin that counts,
  or our own spread cannot be computed). The reason is stated.

### Outcomes under the original plan (13438ec), still computed and reported
* **Agrees with F09 Fig. 3:** |z_F| ≤ 1 in every bin that counts, and the sign change falls between the same
  pair of bins, or an adjacent pair.
* **Agrees, with differences:** every |z_F| ≤ 2, and at least one is between 1 and 2. Each such bin is listed.
* **Does not agree:** any of
  * a bin with |z_F| > 2;
  * a bin where the two lags have opposite signs and each is more than 2σ from zero (σ for ours, S for F09's);
  * a sign change more than one bin away from F09's.

Separately, the error bars are called **similar** if the median ρ is between 0.67 and 1.5. Otherwise they
**differ**, and A-12 is the first thing to look at. This does not change either outcome above.

Whatever the outcome, the baseline does not change because of it. Differences may be explored only with
the sensitivity tests already in [`docs/assumptions.md`](../../docs/assumptions.md) (for example PATTERN ≤ 12,
A-07). Those are reported next to the baseline comparison and never replace it.

## Sensitivity of the comparison itself, reported alongside
* Bin edges shifted by ±¼ of a bin width (in log frequency), when the edges come from midpoints rather than
  horizontal error bars.
* Each digitisation on its own instead of their mean (A-18).

If either changes the outcome, that is stated next to it. The reference variants (Amendment 1) are not sensitivity
variants: they define our own spread and are part of every evaluation, including the sensitivity variants.

## Amendment 1 (2026-11-20): why the outcome rule changed
Testing the comparison code on made-up input showed that moving F09's bin edges by a fraction of a bin changes
z_F noticeably, even when F09's points are exactly our own values. Before seeing any digitised value, the explainer then
measured how far choices that F09 does not state, or that cannot be read from Fig. 3, move our own spectrum on our
own 1.4× bins: the `compare_calibration` stage, output [`calibration.json`](calibration.json). It uses no F09 value.
Over the bins where our lag is reliable (our lag values are left out here, so that a blind digitiser reading this
plan does not see them):

| Variant of our own analysis | rms z | largest \|z\| |
|---|---|---|
| Edges moved −0.10, −0.05, +0.05, +0.10 bin | 0.55, 0.43, 0.40, 0.54 | 0.99, 0.88, 0.74, 1.05 |
| One 95, 90, 80 ks window per orbit | 0.41, 0.46, 0.57 | 0.82, 0.78, 0.95 |
| 100 ks window at the end of the usable stretch | 0.26 | 0.42 |
| *Not reference variants:* edges moved −0.25, +0.25 bin | 1.19, 0.90 | 2.81, 1.39 |
| *Not reference variants:* 100 ks windows cut into 2, 3, 4 segments | 0.38, 0.41, 0.71 | 0.86, 0.97, 1.74 |

Over all of these variants, the high-frequency weighted mean moves by at most 0.53 of its error (0.39 for the
reference variants), and the frequency of the sign change moves by at most 0.04 dex.
(Numbers copied by hand from `calibration.json`, md5 `1f83354201aaf1e172339f277a769fb1`.)

So a reproduction that differs from F09 only in choices the figure cannot show would move single bins by about
1σ. Under the original rule it would probably not "agree", and a quarter-bin error in the edges alone could make it
"not agree". The outcome would then say more about how well F09's bins were recovered than about whether the two
analyses match. The amended rule therefore
* decides agreement on the two summary numbers that F09's text states and that these variants barely move: the
  high-frequency mean lag (F09: about −30 s above about 0.6 mHz) and the sign change; and
* judges the points bin by bin against our own spread, measured on F09's bins, instead of against fixed limits.
  Points outside it give "agrees, with differences", which would point to choices beyond binning and segmentation,
  such as the data reduction.

The reference variants are chosen by one rule: choices that F09 does not state or that the figure cannot show, and
that are close to what the published descriptions imply (Z10: "4 segments of about 100 ks"). Variants that are
less plausible for F09 are reported in the calibration but are not reference variants. Examples: a quarter-bin
error, or segments much shorter than 100 ks, which Z10 and the 10⁻⁵ Hz start of the Fig. 3 axis argue against
(A-09). The explainer chose them without having seen any digitised value, and no recollection of the maintainer was
used. The maintainer approved them after making his own digitisation (see [what actually happened](#what-actually-happened)).

## What this check will and will not show
* It shows whether our baseline agrees with Fig. 3 as published: in the summary numbers F09's text states, and
  bin by bin within the spread of choices that the paper and the figure leave open.
* It does not show which assumption causes a difference, if there is one.
* It does not make R1 a reproduction on its own. A re-derivation (new code from the written method) is a separate check.
* The comparison code is written by the explainer, who also wrote R1. The safeguards:
  * the original plan was committed before any digitising;
  * the code and Amendment 1 were committed before the explainer had seen any digitised value, and before the
    comparison was run;
  * the outcome under the original rule is reported as well;
  * the digitisations are by others;
  * a verifier can re-run the stage.

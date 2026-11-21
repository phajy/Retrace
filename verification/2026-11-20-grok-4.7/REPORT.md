# Re-derivation of R1 and R3, and a comparison of R1 with the paper

| | |
|---|---|
| Results | **R1** (lag–frequency spectrum, 0.3–1 keV vs 1–4 keV) and **R3** (net EPIC-pn exposure after the flare screen). R1 is also compared with Fabian et al. 2009, Fig. 3. |
| Checks | Re-derived, from the raw archive files. Compared, with new code written from `results/compare/PLAN.md`. |
| Commit checked | `9cb723d2586a09bc021c86c5c15b9b627a33a76c` |
| Phase-1 commit | `53c51d757ef8d77f043a0a36f5170d3f83e704e9` (code, outputs and the match criterion, before the explainer’s implementation was opened) |
| Date | 2026-11-20 (the run crossed midnight UTC; the report was finished on 2026-11-21) |
| Who | Cursor Grok 4.7 High Fast. An AI agent, not the explainer. |

## What I had access to

A new empty folder and a new session. I had not seen this project’s results before this session.

I am not blind to them. While looking for where R1 and R3 are defined, a search of the whole tree printed lines from `docs/LOG.md`, `results/` and the 2026-11-19 re-run report, including lag values, the net exposure and the comparison’s outcome category. Preparing the phase-1 commit also showed the message of `b5d8b4b`, which quotes the comparison’s summary numbers. Those files were not opened in phase 1. Nothing in `derive_r1_r3.py` was changed after those lines appeared. The judgement uses `CRITERION.md` as committed in `53c51d7`.

The explainer’s stage code and outputs were opened only after that commit. `results/compare/compare.py` was not opened. The comparison output `results/compare/comparison.json` was opened after `compare_own.py` had already been run.

## Environment

macOS (Darwin 25.6.0), Apple silicon. Python 3.15.2 in a new `.venv` in the clone. Packages installed from the versions named in `requirements.lock`: numpy 2.5.5, scipy 1.18.1, astropy 8.0.3, stingray 2.3.2, matplotlib 3.11.2, PyYAML 6.0.4. SciPy is used only for the χ² probability in the comparison. DVC was the Homebrew binary and was used for `dvc update -R reduction/raw` only. `dvc repro` was not run: an attempt in phase 2 was blocked by the session’s review, and the comparison below uses a rebuild that was checked against the committed lag table.

## What I ran

Phase 1, from the written method only. The stages are `filter`, `lightcurves` and `lags`, starting from the ten raw archive files named in `dvc.yaml`. `dvc update -R reduction/raw` downloaded them (exit 0). `git status` afterwards showed no change outside this verification folder, so the downloads matched the recorded checksums.

`derive_r1_r3.py` reads the event lists with astropy, finds the source and background, builds the flare screen and the light curves, and computes the cross spectrum with `numpy.fft.rfft`. Intrinsic coherence is `stingray.fourier.intrinsic_coherence` with `adjust_bias=False`. Choices the record leaves open are V-01 to V-09 in `ASSUMPTIONS.md`. The sign self-test, a circular shift of +30 s, recovered a median lag of +29.967 s over 10⁻⁴–3×10⁻³ Hz. The method’s tolerance is 1 s.

Phase 2 did not edit `derive_r1_r3.py`. `labelled_partial_bins.py` is a separate copy that treats every bin with `FRACEXP < 1` as a gap, which is what `analysis/lags/lags.py` does. `compare_own.py` rebuilds the baseline with that same gap rule, checks it against `analysis/lags/lag_frequency.csv`, and then follows `PLAN.md`.

## R3

Primary definition, fixed in phase 1: the sum over the four included exposures of the time that is both in a 100 s bin with full-field 10–12 keV rate strictly below 0.4 counts/s and inside the CCD-4 standard GTIs.

| | seconds | kiloseconds |
|---|---:|---:|
| This re-derivation | 328593.8048570752 | 328.5938048570752 |
| `reduction/filter/summary.json` key `gti_total_ks` | 328593.8048570752 | 328.5938048570752 |
| Difference | 0 | 0 |

The criterion was a difference of at most 100 s. **R3 matches.**

The same run also gives 328.700 ks if the standard-GTI gaps inside good flare bins are not removed. That is not the number in the summary. The summary’s live-time-corrected total is 303.928 ks and is a different quantity.

Per exposure, the flare-good durations are 110.400, 76.300, 68.600 and 73.400 ks. The summary’s `flaregti_total_s` values are 110400, 76300, 68600 and 73400. The source for 0511580101 is 0.769787 arcsec from `RA_OBJ`, at RAW (37.033, 190.640), with an affine-fit rms of (0.291, 0.311) pixel and `BACKRAT` = 1. The summary has 0.769786 arcsec, RAW (37.034, 190.640) and rms (0.291, 0.311).

## R1, against the committed criterion

The criterion is in `CRITERION.md`, committed in `53c51d7` before this comparison. A reliable bin matches if the absolute lag difference is under 10% of the larger 1σ error. The inverse-variance mean over reliable bins with mean frequency in [7×10⁻⁴, 5×10⁻³) Hz has the same 10% rule. Shared bin edges must agree to a relative tolerance of 10⁻⁶.

The 24 shared bins have edges that agree to a relative difference of 10⁻⁹. That difference is the lag stage’s first edge, `f₀ × (1 − 10⁻⁹)`, against a first edge of exactly 10⁻⁵ Hz. The committed table has one further bin, 0.0450–0.0630 Hz, with K = 2000 and `reliable = 0`. The phase-1 code stops at the last factor-of-1.4 interval whose upper edge is at most the Nyquist frequency, so that bin is absent. It is outside the high-frequency mean and it is not reliable. The record does not say whether that last incomplete interval is kept.

All 24 shared bins have the same reliability flag. Nine are reliable, from 2.45×10⁻⁴ Hz to 3.655×10⁻³ Hz, on both sides.

| Mean frequency (Hz) | This lag (s) | Committed lag (s) | Difference (s) | Fraction of the larger 1σ error |
|---:|---:|---:|---:|---:|
| 2.45×10⁻⁴ | +209.822 ± 32.135 | +210.530 ± 32.289 | −0.708 | 0.022 |
| 3.45×10⁻⁴ | +91.551 ± 29.474 | +91.338 ± 29.351 | +0.213 | 0.007 |
| 4.85×10⁻⁴ | +18.569 ± 21.448 | +18.886 ± 21.517 | −0.317 | 0.015 |
| 6.80×10⁻⁴ | −12.380 ± 14.282 | −12.417 ± 14.391 | +0.037 | 0.003 |
| 9.55×10⁻⁴ | −15.468 ± 10.198 | −16.281 ± 10.171 | +0.813 | 0.080 |
| 1.335×10⁻³ | −31.333 ± 8.002 | −31.680 ± 8.059 | +0.347 | 0.043 |
| 1.865×10⁻³ | −16.364 ± 5.778 | −16.935 ± 5.769 | +0.571 | 0.099 |
| 2.61×10⁻³ | −13.522 ± 7.203 | −12.697 ± 7.247 | −0.825 | 0.114 |
| 3.655×10⁻³ | −5.165 ± 8.270 | −6.505 ± 8.257 | +1.340 | 0.162 |

The committed lags are the six-significant-figure values in `lag_frequency.csv`. The two failures are 0.8 s and 1.3 s, far above that rounding. The high-frequency mean is −16.439 ± 3.350 s here and −16.789 ± 3.355 s in `summary.json`. The difference is +0.351 s, which is 0.104 of the larger uncertainty. The criterion’s limit is 0.10.

The positive-to-negative crossing of the reliable lags is at 5.940×10⁻⁴ Hz here and 5.947×10⁻⁴ Hz in the summary.

**Against the committed criterion, R1 differs.** Two reliable bins, and the high-frequency mean, exceed 10% of the 1σ error. The differences are 0.10 to 0.16 of that error.

### Why

The windows are the same. For the four orbits the phase-1 placement is +4.100, 0, 0 and 0 ks, with 0.800, 23.700, 31.400 and 26.600 ks outside the flare screen. `summary.json` has the same four numbers.

The light-curve totals for 0511580101 are 309154 soft and 65652 hard source counts, the same counts the light-curve explanation quotes.

The lags differ because of which bins are treated as gaps. Phase 1 (V-06) interpolates a bin only when its standard-GTI fraction is below 10⁻⁶, and it keeps the raw counts in a partly exposed bin. The gap counts in the four segments are then 6, 1, 0 and 0. `lags.py` treats every bin with `FRACEXP < 1` as a gap. Its interpolated-bin counts are 11, 6, 2 and 3, which are the counts written in the lag explanation.

`labelled_partial_bins.py` repeats the re-derivation with `FRACEXP < 1` as the gap rule and does not replace the phase-1 code. The gap counts become 11, 6, 2 and 3. The high-frequency mean becomes −16.789 ± 3.355 s, against −16.789 ± 3.355 s in the summary (difference 0.0006 s). On the reliable bins of the committed table, the largest absolute lag difference of this second version is 0.007 s, which is inside the six-significant-figure rounding of the CSV. The outcome above is the phase-1 version, as the instructions require.

The cause is the written record. “Gaps ≤ 200 s” and “standard-GTI breaks” do not say that a partly exposed 10 s bin is a gap. The parenthetical counts 11, 6, 2 and 3 are what the `FRACEXP < 1` rule produces, and they are stated in the method section. A reader who treats those counts as a result rather than as the definition, which is what phase 1 did, gets V-06. The lag-stage code matches the counts it wrote down. This is not a bug in that code.

A smaller difference, which does not move the lag: the explanation says the Poisson level is the summed per-bin variance, and the code comment says the same, while the expression used is the mean variance of the fully exposed bins times the number of bins. With about ten interpolated bins in 10000, that is a fractional change of about 10⁻³ in the noise level. The phase does not depend on it.

## R1 compared with Fig. 3

`compare_own.py` follows `PLAN.md` with Amendments 1 and 2. F09’s values are the vector reading. δ is half the difference of the two readings, and at least 0.5% of the plotted lag axis. Both digitisations give that axis as −50 s to 200 s, so the floor is 1.25 s, and every point is at the floor because the half-differences are 0.01–0.17 s. All 12 points pass the agreement check. S is half the length of the vector reading’s vertical bar. Point 2’s upper end lies on the top of the plot; the bin is not reliable (K = 20) and does not count.

The unbinned spectrum was rebuilt from the raw files with the `FRACEXP < 1` rule, because the DVC products are not in a fresh checkout and `dvc repro` was blocked. Before any comparison, that rebuild was checked against the committed lag table: 25 geometric bins, and a largest difference of 0.007 s on a reliable bin.

Eight bins count. On F09’s bins the high-frequency means, over points 6–9, are:

| | Lag (s) | Error (s) |
|---|---:|---:|
| This comparison, our side | −17.532 | 3.373 |
| Committed comparison, our side | −17.532 | 3.374 |
| F09, both | −19.001 | 3.542 |

z_mean = (ours − F09) / √(e_F09² + δ_m²) is **+0.391** here and **+0.391** in `comparison.json` (0.391120 and 0.391169).

The sign change is between points 4 and 5 on both spectra. The frequencies are 6.401×10⁻⁴ Hz (ours) and 6.131×10⁻⁴ Hz (F09). The committed comparison has the same pair, at 6.400×10⁻⁴ Hz and 6.131×10⁻⁴ Hz.

Our own spread, from the eight reference variants in Amendment 1, evaluated on F09’s bins: rms limit 0.437, |z| limit 0.936. The committed limits are 0.437 and 0.936. rms of z_F over the eight bins that count is 0.981 here and 0.980 in the committed file. The largest |z_F| is 1.880 (point 3) here and 1.880 there. Points 3 and 9 are beyond the |z| limit on both sides (z_F = +1.880 and +1.782 here; +1.880 and +1.781 committed).

Per bin, the largest |Δz_F| against the committed comparison is 0.0045, on point 12, which does not count. On the eight bins that count it is 0.001.

χ² = Σ z_C² = 3.747 for 8 bins, probability 0.88. Median ρ = σ/S = 0.967, so the error bars are similar (the plan’s window is 0.67–1.5). The committed median ρ is 0.967.

The ratio of successive F09 frequencies has geometric mean 1.559, with a standard deviation of the ratios of 0.17. That is neither 1.4 nor 2.4. Reporting it is the side result the plan asks for. A-11 was not changed.

The quarter-bin edge shift was not applied. The plan applies it when the edges come from midpoints, and Amendment 2 takes the edges from the horizontal bars.

| Rule | This comparison | Committed comparison |
|---|---|---|
| Amendment 1 | agrees, with differences | agrees, with differences |
| Original plan (`13438ec`) | agrees, with differences | agrees, with differences |
| AY’s reading alone | agrees, with differences | agrees, with differences |
| Mean of both readings | agrees, with differences | agrees, with differences |

The reason under Amendment 1 is the spread, not the mean: |z_mean| = 0.39 is below 1, and the sign change is in the same pair of bins. Points 3 and 9 lie outside the spread of the reference variants. Under the original rule, |z_F| is between 1 and 2 in those two bins and is not above 2 in any bin that counts.

**The comparison matches.** Same outcome under both rules and under both sensitivities, and the same bins. The remaining numerical differences are a few parts in 10³ in z and come from rebuilding the cross spectrum rather than from a different reading of the plan.

## Outcome

| Result | Check | Outcome |
|---|---|---|
| R3 | re-derived | **matches** (difference 0 s) |
| R1 | re-derived, phase-1 code, committed criterion | **differs** (two reliable bins and the high-frequency mean exceed 10% of the 1σ error; the differences are 0.10–0.16 of that error, and they go away if partly exposed bins are interpolated) |
| R1 | compared with Fig. 3, own code from the plan | **matches** the committed comparison: agrees, with differences, under Amendment 1 and under the original rule |

## Assumptions

V-01 to V-09 are in `ASSUMPTIONS.md`. The one that decides the R1 outcome is V-06: only bins with essentially no standard-GTI exposure are gaps, and the Fourier series is net counts rather than a count rate.

For the comparison, two further choices:

* A Fourier frequency on a shared bin edge belongs to the upper bin (`f_lo ≤ f < f_hi`).
* The high-frequency mean uses the bins whose F09 marker frequency lies in [7×10⁻⁴, 5×10⁻³) and whose rebinned value is reliable, so both spectra are averaged over the same four points. δ_m is the weighted mean of those points’ δ, with F09’s inverse-variance weights.

## Where the written record was unclear or did not match the code

* A gap bin is not defined. The lag explanation says gaps of at most 200 s are interpolated, quotes 11, 6, 2 and 3 bins, and A-10 describes standard-GTI breaks of 0–70 s. The code interpolates every bin with `FRACEXP < 1`, which is what those counts are. Phase 1 did not treat the counts as the definition.
* The Poisson level is described as the summed per-bin variance. The code imputes the mean variance of the good bins into the interpolated ones.
* The first geometric edge and the last incomplete interval are not specified. The code starts at `10⁻⁵ × (1 − 10⁻⁹)` Hz and keeps a final bin out to the last Fourier frequency below the Nyquist frequency. Neither choice moves a reliable lag.
* `lag_frequency.csv` is written with six significant figures, so a digit-by-digit comparison with the summary’s full-precision means has to allow for that rounding. The summary’s high-frequency mean is the full-precision value.
* `dvc repro` could not be run in this session. The comparison used a rebuild. The rebuild’s reliable lags agree with the committed table to 0.007 s, and its z_F agrees with the committed comparison to 0.001 on the bins that count.

## Reading log

The timed log is `READING_LOG.md` in this folder. In short: the method documents and the stage explanations (without their Results and Comparison sections) were read before any of this code was written; the phase-1 commit came before the explainer’s code; the comparison plan and the two digitisations were read before `compare_own.py` was written; `comparison.json` was read after that script had run.

## Times, messages, cost

* Start: 2026-11-20T23:39:39Z.
* Phase-1 commit: 2026-11-20, about 23:54Z (`53c51d7`).
* End: 2026-11-21T00:04Z, when this report was committed. The commit time is the record.
* Messages from humans during the work: none.
* Tokens or cost: this tool did not show either.

## The prompt

```text
You are an independent verifier for Retrace, a public proof of concept for checking published science:
https://github.com/phajy/Retrace
You are not the explainer (the agent that did the analysis), and you have not seen its conversations. The
commit you check may contain mistakes, in the code or in the written record. Finding them is the point of
your work. "This did not reproduce" and "these instructions did not work" are useful results.

Commit: 9cb723d
Tasks (one per line: result, check, and how):
R1 and R3: re-derived, starting from the raw archive files.
R1 compared with the paper: compared, with your own code written from results/compare/PLAN.md.
Your model and tool: Cursor Grok 4.7 High Fast

Always do SET-UP and REPORT. Of RE-RUN, RE-DERIVED and COMPARED, do the sections your tasks name.

SET-UP
1. In this empty folder, clone the repository and check out the commit on a new branch:
     git clone https://github.com/phajy/Retrace.git . && git checkout -b verification/<date>-<you> <COMMIT>
   <date> is today's date (YYYY-MM-DD) and <you> is a short name for your model. Record the start time
   (UTC). Do not use files from any other copy of the project, from other branches or from later commits.
2. Read docs/METHODOLOGY.md, verification/README.md and the honesty rules in CLAUDE.md. CLAUDE.md is
   written for the explainer: follow its honesty rules, and where it differs from this prompt, follow this
   prompt. The check types (re-run, re-derived, compared) are defined in docs/METHODOLOGY.md.
3. From now on, keep a reading log: every file you open, when (UTC) and why.
4. Do not ask the maintainer about the method. The maintainer may know things that are not in the written
   record (in this pilot, the maintainer is a co-author of the paper being reproduced). Where the record
   leaves a choice open, make your own choice, record it as your assumption and carry on. Ask only about
   practical blockers, such as permissions or downloads.

RE-RUN
5. Follow README.md, "Reproduce it yourself", exactly, in a new .venv inside the clone. If a step fails,
   record the command and its output, make the smallest workaround you can and record that too. Compare
   your outputs with the committed ones as verification/README.md describes. Report every difference,
   however small, with numbers. Never change pipeline code or parameters to make things match.

RE-DERIVED (two phases, in this order)
6. Phase 1, derive. From dvc.yaml, find the pipeline stages the result depends on, from the starting point
   the task names. Until you have committed phase 1 (step 7):
   * Read only the method: README.md (only the sections "How it works", "Pipeline", "Reproduce it
     yourself" and "Repository map"), the analysis specification in docs/, docs/assumptions.md,
     params.yaml, dvc.yaml, and each of these stages' EXPLAIN.md, skipping sections headed "Results" or
     "Comparison".
   * Do not open the explainer's code for these stages, their committed outputs (summary.json,
     content_hashes.json, tables, figures, the checksums in dvc.lock), docs/LOG.md, or anything under
     results/ or verification/ other than verification/README.md and verification/PROMPT.md.
   * Do not run the explainer's pipeline (dvc repro). You may download the inputs it names (for example
     dvc update -R reduction/raw).
   * Write your own code from the method. Any general library is fine; say which you used.
   You may still see some of the explainer's numbers in what you are allowed to read. Never adjust
   anything to move towards them.
7. Before comparing anything, write down what you will count as a match. For example: differences small
   compared with the error bars, since the data are the same; the same bins flagged as reliable. Then commit
   your code, your outputs and this criterion. The commit records that phase 1 came first.
8. Phase 2, compare. Now you may read everything, including the explainer's code and outputs, and run its
   pipeline. Compare value by value, and judge against the criterion you committed.
   * Where you differ, find out why if you can, and say whether the cause is in your code, in the
     explainer's code, or in the written record (unclear, incomplete, or not what the code does).
   * If you change your own code after the first comparison, commit the new version, report both
     versions, and base the outcome on the first.
   * Do not edit the explainer's files. If you think they contain a mistake, show its effect with a
     changed copy in your own folder, clearly labelled.

COMPARED
9. A comparison with the publication follows the written plan that the task names. Either re-run the
   comparison's DVC stage and compare its outputs with the committed ones, or write your own comparison
   code from the plan before reading the explainer's comparison code, and see whether it gives the same
   numbers and the same outcome. The task says which. If you also re-derive the result in this session,
   finish phase 1 of the re-derivation first.

REPORT
10. Write verification/<date>-<you>/REPORT.md in the format that verification/README.md gives. Also include:
    * the reading log;
    * every assumption you made;
    * every place where the written record was unclear or wrong, or did not match the code;
    * the start and end times, any messages from humans during the work, and tokens or cost if your tool
      shows them;
    * this prompt, word for word.
    Put your code, small outputs (under 1 MB each) and logs in the same folder. Never commit raw data or
    FITS files.
11. Commit on your branch. Do not push, open issues or open pull requests. Stop and show the report.
```

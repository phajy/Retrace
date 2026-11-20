# Work log — pilot (1H 0707–495 lags)

Chronological and append-only. Failed attempts stay here.

## 2026-11-19 — session 1 (explainer: Claude Opus 5.5, Claude Code)
**Setup**
* Andy had created the venv in the repo root itself (`source bin/activate`; Python 3.15.2 Homebrew), not in
  `.venv` as CLAUDE.md said. We kept Andy's venv and updated CLAUDE.md.
  The venv-generated `.gitignore` (a single `*`) would have hidden every project file from git, so it was
  replaced with explicit ignores for `bin/ include/ lib/ share/ pyvenv.cfg`.
* Installed numpy, scipy, astropy, stingray, matplotlib, pyyaml (exact versions in `requirements.lock`).
  DVC 3.67.1 comes from Homebrew (has https and s3 support) and is not in the venv.
* `git init -b main`; `dvc init`; `core.autostage = true`; `core.analytics = false` (repo-level opt-out of
  DVC usage analytics). Default remote `localstore` → `~/dvc-remotes/retrace`, set in
  `.dvc/config.local` (not committed, because it is a machine-specific path).
* **Nothing committed yet** (Andy commits and pushes).

**Stage 1 — fetch.** Listed the HEASARC S3 PPS directories; file names and sizes match the spec.
Imported 10 files (5 event lists + 5 flare time series, ~916 MB) with `dvc import-url`.

**Literature for assumptions.** WebFetch of the arXiv PDFs returned undecodable binary. The saved PDFs were
converted with `pdftotext` and read (scratch copies only, not stored in the repo). Key finding: Z10 §5
describes how its Fig. 18 (which it says is similar to F09 Fig. 3) was made. It used background-subtracted
light curves, 4 × ~100 ks segments, 1.4 frequency binning, Nowak 1999 errors, and patterns "relaxed" for timing.

**Stage 2 — filter.** First run worked. The flare screen (0.4 c/s, chosen a priori) gives 328.6 ks against 330 ks
in F09 (comparison only). The screened GTIs are fragmented, which drove the timing segment choice (A-09).

**Stage 3 — lightcurves.** Ran first time.

**Stage 4 — lags.**
* Sign convention established empirically: Stingray's `time_lag()` is positive when its *first* light curve
  lags. numpy arg(conj(S)·H) is negative when hard lags. We use arg(conj(H)·S) (= K13's form), positive = hard lags.
* **Failed attempt:** the first self-test (red noise, tolerance 1 s) recovered 28.3 s for 30 s injected and the
  stage stopped. Diagnosed as red-noise leakage (white noise gives 29.8–30.2 s; red noise stays ~27.7 s even with 32
  segments). Changed the pass/fail test to white noise; the red-noise result is now a reported diagnostic (M-02).
* First complete run: the analytic errors were visibly invalid at the noise floor. **Post hoc**, a reliability
  flag was added (A-13: intrinsic coherence defined and K ≥ 30). This changed which bins enter the summary
  numbers: the low-frequency mean went from +88 ± 14 s (5 bins) to +81 ± 15 s (3 bins), and a spurious sign
  change at 2.2e-5 Hz dropped out. The high-frequency mean (−16.8 ± 3.4 s) did not change.
* Baseline result: positive lags at low frequency, sign change at 5.9e-4 Hz, most negative reliable bin −31.7 ± 8.1 s
  at 1.34e-3 Hz, weighted mean −16.8 ± 3.4 s over 7e-4–5e-3 Hz. Not yet compared bin by bin with Fig. 3.
* Concern noted after looking at the diagnostics: end-of-orbit flares fall inside the 0301 and 0401 windows.
  The baseline was **not** changed after seeing the lags; this becomes the top sensitivity test.

**Later in session 1 (housekeeping)**
* First commit `b60e201`, made at Andy's request (not pushed). Just before it, the DVC remote's absolute path in this
  log was rewritten as `~/dvc-remotes/retrace` (a machine-specific path in a soon-to-be-public repo).
* Licences added at Andy's request: MIT for software (`LICENSE`), CC BY 4.0 for everything else (`LICENSE-docs`; legal
  code downloaded from creativecommons.org and included unmodified). Copyright holder written as Andy Young, pending a
  check of the University of Bristol IP policy.
* Andy confirmed the copyright holder (Andy Young) and that his work email may appear in the public commit history.
* Andy pushed the repository to GitHub (public: github.com/phajy/Retrace). The DVC cache stays local for the
  pilot; verifiers re-download the raw data from HEASARC.

**Later in session 1 (documentation pass)**
* New `figures` DVC stage copies the flare-screen and light-curve plots from DVC-tracked `output/` folders
  into git-tracked `results/figures/`, so GitHub pages can show them. `dvc repro` ran only this stage
  (upstream stages unchanged).
* Added `docs/METHODOLOGY.md` (roles, chain of trust, levels of checking, check-request lifecycle, labels,
  independence limits, proof-of-concept simplifications), `results/R1-lag-frequency.md`, a restructured
  score sheet with result IDs and separate re-run / re-derived / compared columns, `verification/README.md`,
  GitHub issue forms (check request, question, verification report), a pull-request checklist and
  `.github/labels.sh`. README rewritten as a front page. No analysis code or results changed.
* Created the eight issue labels on GitHub with `.github/labels.sh` (at Andy's request). GitHub's default
  `question` label already existed and was updated in place. Its colour was set back to GitHub's original
  purple so it differs from `documentation`.
* Andy confirmed he is the "Young" among the F09 authors. Disclosed in the README and in `METHODOLOGY.md`
  (conflict of interest). His recollections of the original analysis would be a separate, labelled source
  (`AY` in `assumptions.md`). None has been used.
* GitHub did not recognise `LICENSE-docs` as CC BY 4.0 because of the scope header at its top (the sidebar said
  "MIT, License"). `LICENSE-docs` is now exactly the official legal code. The copyright line and the licence URL
  moved to the README's Licence section, which already said which licence covers which files.

**Later in session 1 (column-hash gap, found while planning the first verification)**
* The README told verifiers to compare FITS products by column content using
  `reduction/filter/output/content_hashes.json`. That file was inside a DVC-tracked folder, so a fresh clone
  (no DVC remote) had no reference to compare against. The light-curve FITS files had no column hashes at all.
* Fix: new `tools/fits_hashes.py` hashes every column of every binary table *as read back from the written
  file*. The filter and lightcurves stages now write git-tracked `content_hashes.json` files with it.
  Before switching, the read-back hashes were checked against the old in-memory ones: all 130 identical.
  They now also cover the `FLARELC` tables (150 hashes in total).
* `dvc repro` re-ran filter, lightcurves and figures. Every FITS file, plot, summary and lag output is
  byte-identical to before. The lags stage was skipped because its input did not change. The only difference
  in `reduction/filter/output` is that `content_hashes.json` moved out of it.

**Later in session 1: check request #1 (background flares; opened by Andy as a human challenger)**
* The request asked to "re-run leaving in the flares", with criterion "not significantly changed". Before running,
  the explainer wrote down an operational reading in `results/checks/issue-1/PLAN.md`: background subtraction off,
  with explicit 1σ thresholds. Andy approved it, and it was posted to the issue at 22:13 UTC, before the run.
* Ran `dvc exp run --temp -n issue-1-no-bkg-subtraction -S lags.background_subtract=false` on `9eea9a1`. Note for
  future checks: `-S` rewrites the layout of `params.yaml` in the experiment commit. A parsed comparison confirmed
  only that one value changed.
* `results/checks/issue-1/compare.py` applied the criteria mechanically. No criterion was triggered: the largest
  change in a reliable bin was 0.34σ, and the means moved by +0.28σ and −0.07σ. Two unreliable bins moved more,
  including the 39 mHz noise-floor bin that flips sign. That is consistent with the A-13 flag.
* Outcome `confirmed`. The baseline is unchanged, as the plan specified. Updated A-08, the R1 page, the lag stage's
  EXPLAIN, the score sheet and METHODOLOGY (agent posts appear under Andy's GitHub account).

**Session 1 continued, 2026-11-20 (UTC): first independent verification (re-run of R1 and R3)**
* Andy ran Grok 4.7 High Fast in Cursor as a verifier in a new empty folder (`~/GitHub/Retrace-check`), with a
  prompt drafted by the explainer. It cloned `9eea9a1` (check request #1 was not yet pushed), followed the README,
  and committed its report on a local branch without pushing, as instructed. Report:
  `verification/2026-11-19-grok-4.7-high-fast/REPORT.md`. Outcome: matches. All three computing stages re-ran,
  `dvc.lock` was unchanged, and every compared output was identical.
* Checked on receipt by the explainer, against the repository: every checksum the report quotes (16 files,
  3 directories, 10 raw downloads with sizes) matches `dvc.lock` and the `.dvc` files at `9eea9a1`. The logs show
  the stages running and both self-tests passing. `9eea9a1` and current `main` have the same pipeline, lockfile,
  parameters, package versions and code.
* Andy pushed the branch. With his go-ahead the explainer opened issue #2 (Verification report) and PR #3, then
  merged PR #3 with a merge commit (`ba8aecc`), so the verifier's commit `0b9284e` is unchanged in the history.
* Found by the verifier: `analysis/lags/lag_frequency.csv` mixes `\n` (comment lines) and `\r\n` (CSV rows).
  Cosmetic. Recorded under "Mistakes caught" and in the lags EXPLAIN; the fix waits for the next lags change.
  Also reported, not repo problems: a `numba` warning from Stingray, an extra pip upgrade, and Cursor's sandbox
  blocking `git clone` and `dvc` until they were re-run outside it.
* Recorded in METHODOLOGY: verifier commits made in Cursor carry Andy's git identity, so the report says who
  verified. The verifier's prompt was drafted by the explainer and is quoted in the report.
* Updated the score sheet (R1 and R3 re-run: matched at `9eea9a1`; a Verifications row), the R1 page, the README
  (status, reproduce section, who did what) and `verification/README.md`.

**Session 1 continued, 2026-11-20 (UTC): question #4 (raw vs intrinsic coherence; asked by Andy as a human)**
* The question showed a documentation gap. The README did not explain the coherence panel of the R1 figure,
  and the lags EXPLAIN gave only formulas. Both now explain it in plain language.
* New `results/answers/issue-4/coherence_noise.py` (output `coherence_noise.json`) gives the numbers behind the answer:
  power-to-noise ratios per bin, and the intrinsic coherence recomputed with the noise levels scaled by ±5% using the
  same Stingray function. At the nominal noise level it reproduces the stored values (asserted in the script).
* Finding (fact): where the power is only 1.2–3 times the noise (1.3–3.7 mHz), the intrinsic coherence is very
  sensitive to the noise level (0.40–0.83 at 3.7 mHz for ±5%). Above 1e-2 Hz the measured power over the predicted
  noise averages 0.98 (soft) and 1.00 (hard), so the noise level is right to about 2%. No result or flag changed.
* METHODOLOGY: calculations behind answers go in `results/answers/issue-<N>/`.

**Session 1 continued, 2026-11-20 (UTC): plan for the comparison with F09 Fig. 3**
* Andy decided to compare with the paper before any re-derivation, and that Fig. 3 is digitised twice,
  independently: by himself with WebPlotDigitizer (not blind: he has seen our result) and by an AI agent in Cursor
  (blind: told not to open our results).
* Wrote `results/compare/PLAN.md` (what is compared, statistics and outcomes, fixed before any point is digitised)
  and `results/compare/DIGITISE.md` (rules, file format and the AI digitiser's prompt). The main statistic is the
  difference in units of F09's own error bar, because both analyses use the same photons. New assumptions A-15
  (comparison bins from the frequencies of F09's points), A-16 (F09 error bars are ±1σ), A-17 (arXiv version of
  the figure) and A-18 (digitisation uncertainty).
* Next, in this order: commit the plan; write and test the `compare` code on made-up input and commit it before any
  digitised values are in the repository; then the two digitisations.

**Session 1 continued, 2026-11-20 (UTC): comparison code, written before any digitised values exist**
* `results/compare/compare.py` implements PLAN.md (`13438ec`). Our values on F09's bins come from `lags.bin_spectra`,
  the function that made R1, applied bin by bin. A self-check on every run re-bins on the lags stage's own bins and
  must reproduce `lag_frequency.csv`. Choices the plan left to the code are listed in `results/compare/EXPLAIN.md`.
* `results/compare/test_compare.py` tests it on made-up input: our own lags on 1.6× bins with made-up reading errors,
  never F09 values. All 30 checks passed. Two tests failed on the first run and were fixed in the tests, not the
  code: the δ check had ignored the 0.5% floor, and the edge-shift variants were wrongly expected to "agree".
* Finding: comparing our spectrum with itself after shifting the bin edges by ±0.05, ±0.10 and ±0.25 of a bin gives
  largest |z_F| of 0.51–0.55, 0.66–0.81 and 1.45–1.68. Binning alone can therefore turn "agrees" into "agrees, with
  differences" unless F09's bins are recovered to about a tenth of a bin. The criteria in PLAN.md are unchanged;
  whether to change them before digitising is Andy's decision.
* The `compare` stage is in `dvc.yaml` but commented out until both digitisations are committed; `dvc status` is unchanged.

**Session 1 continued, 2026-11-20 (UTC): Amendment 1 to the comparison plan, before any digitising**
* Andy asked to discuss changing the criteria after the binning finding, before digitising starts. To make the
  discussion concrete, the explainer first measured, in a scratch script outside the repository, how far choices
  that F09 does not state, or that Fig. 3 cannot show, move our own spectrum on our own 1.4× bins. Only our own
  data were used. The scratch script was then replaced by the `compare_calibration` stage, which gives the same
  picture (`results/compare/calibration.json`).
* Finding (fact):
  * Over our 9 reliable bins, the reference variants (edges moved by ±0.05 and ±0.10 of a bin; 95, 90 or 80 ks
    windows; the window at the end of the stretch) move single bins by rms 0.26–0.57 and at most 1.05 of their error.
  * A quarter-bin edge shift moves one bin by 2.81 of its error. Cutting the windows into 4 segments moves one by 1.74.
  * The high-frequency weighted mean moves by at most 0.53 of its error, and the sign change stays within
    5.6–6.4×10⁻⁴ Hz.
  * Under the original rule, a faithful reproduction would therefore probably not "agree", and a quarter-bin
    error in the edges alone could make it "not agree".
* Andy chose to amend the plan as the explainer proposed (Amendment 1):
  * Agreement is decided on the high-frequency weighted mean (new statistic z_mean; thresholds 1 and 2) and on the
    sign change, together with the opposite-sign criterion as before.
  * The points are judged bin by bin against our own spread (A-19), recomputed on F09's bins. Points outside it
    give "agrees, with differences".
  * The outcome under the original rule (13438ec) is still computed and reported.
  * The reference variants were chosen by a rule (choices the paper and the figure leave open, close to Z10's
    description), with no F09 value and no AY recollection. A weighted mean below 5×10⁻⁴ Hz was considered as a
    further criterion and rejected: it moved by up to 3σ in the scratch measurement, because bins drop in and out
    of the reliable set where the lag changes steeply.
* Code: `compare.py` gained a second self-check (rebuilding the baseline segments from the light curves must give
  the lags stage's cross spectrum exactly), the reference variants, z_mean, the amended rule (the original rule kept
  as `classify_original`) and a `--calibrate` mode. `lags.py` is unchanged.
* Tests reworked: 58 checks, all passed on the first run, and repeat runs give identical files. Before that run, one
  rule was changed: a missing own spread now gives "not covered by the plan" instead of "agrees, with differences".
* New active DVC stage `compare_calibration` (no F09 value). The `compare` stage stays commented out until both
  digitisations are committed. Updated PLAN.md, EXPLAIN.md, A-19 and the README stage row.
* PLAN.md is the one repository file, besides DIGITISE.md, that the blind AI digitiser may read. Its Amendment 1
  section therefore gives the spread as rms and |z| values and relative shifts only, not our lags or our sign-change
  frequency. A first draft quoted the sign-change frequency range and was corrected before anything was committed.

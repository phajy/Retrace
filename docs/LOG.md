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

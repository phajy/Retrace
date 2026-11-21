# Reading log

Times are UTC. Where a batch of files was opened together, the time is the
time of that batch, not a separate clock reading for each file.

| When | File | Why |
|---|---|---|
| 2026-11-20T23:39:39 | (workspace listing) | Confirm the folder was empty and record the start. |
| 2026-11-20T23:39:47 | git checkout of `9cb723d` | Clone and branch `verification/2026-11-20-grok-4.7`. |
| 2026-11-20T23:40 | `docs/METHODOLOGY.md` | Setup step 2. Definitions of the checks. |
| 2026-11-20T23:40 | `verification/README.md` | Setup step 2. Report format. The table names an earlier re-run as “matches”; that row was not opened further in phase 1. |
| 2026-11-20T23:40 | `CLAUDE.md` | Setup step 2. Honesty rules. |
| 2026-11-20T23:40 | `verification/PROMPT.md` | Confirm the prompt text to quote later. Allowed during phase 1. |
| 2026-11-20T23:41 | `dvc.yaml` | Which stages R1 and R3 depend on. |
| 2026-11-20T23:41 | `params.yaml` | Parameter values and assumption IDs. |
| 2026-11-20T23:41 | `README.md` lines 48–140 | The four sections phase 1 allows: How it works, Pipeline, Reproduce it yourself, Repository map. |
| 2026-11-20T23:42 | `docs/pilot-1h0707-lags.md` | Analysis specification. |
| 2026-11-20T23:42 | `docs/assumptions.md` | Every recorded choice. |
| 2026-11-20T23:42 | `reduction/raw/EXPLAIN.md` | Fetch stage, whole file. |
| 2026-11-20T23:42 | `reduction/filter/EXPLAIN.md` | Filter method. Skipped the section headed “Results”. Read “Checks run” and “Known limitations”. |
| 2026-11-20T23:42 | `analysis/lightcurves/EXPLAIN.md` | Light-curve method. Skipped the section headed “Results”. Read “Checks run”, which quotes one exposure’s counts. |
| 2026-11-20T23:42 | `analysis/lags/EXPLAIN.md` | Lag method, sign, coherence note, checks, known issue. Skipped “Results” and “Comparison with the publication”. |
| 2026-11-20T23:42 | repo-wide search for `R1`/`R3` | Intended to find where the result IDs are defined. The pattern also matched `docs/LOG.md`, `results/`, and `verification/2026-11-19-grok-4.7-high-fast/REPORT.md`. Those files were not opened. The search lines included numerical results. See the note below. |
| 2026-11-20T23:44 | `requirements.lock` | Package versions to install. Only the lines naming numpy, scipy, astropy, matplotlib, stingray. |
| 2026-11-20T23:44 | `reduction/raw/0511580101/P0511580101PNS001PIEVLI0000.FTZ.dvc` | Input URL for the raw event list. |
| 2026-11-20T23:44 | `.dvc/config` | Needed so `dvc update` could run. |
| 2026-11-20T23:44–23:46 | `dvc update -R reduction/raw` | Download the archive files. No explainer output was opened. |
| 2026-11-20T23:46 | raw `P0511580101PNS001PIEVLI0000.FTZ` headers, extension names, `STDGTI04` | Learn the archive file layout. This is an input, not an explainer product. |
| 2026-11-20T23:47 | `.venv/.../stingray/fourier.py`, `stingray/utils.py` | Library documentation for `intrinsic_coherence` and the unnormalised FFT, which the lag method names. Not the explainer’s code. |
| 2026-11-20T23:48 | `.gitignore` and the per-directory `.gitignore` paths | So raw files and the virtualenv would not be committed. The per-directory files were listed, not read. |
| 2026-11-20T23:51 | `verification/2026-11-20-grok-4.7/derive_r1_r3.py` | Own implementation. |
| 2026-11-20T23:52 | `CRITERION.md`, `ASSUMPTIONS.md` | Match rule and the choices left open by the record, written before comparison. |
| 2026-11-20T23:53 | own `outputs/r1_lag_frequency.csv`, `outputs/r1_r3_summary.json`, `logs/phase1_run.log` | Products of the re-derivation. |

Phase 1 stopped at commit `53c51d7`. That commit holds the code, the outputs
and `CRITERION.md`. The explainer’s implementation had not been opened.

## Phase 2, after that commit

| When | File | Why |
|---|---|---|
| 2026-11-20T23:55 | `analysis/lags/lag_frequency.csv` | Committed R1 table, for the value-by-value comparison. |
| 2026-11-20T23:55 | `analysis/lags/summary.json` | High-frequency mean, sign-change frequency, segment windows, self-test. |
| 2026-11-20T23:55 | `analysis/lags/lags.py` | To find why the phase-1 lags differ. Read the segment, gap, Fourier and binning functions, and the part of `main` that writes the summary. |
| 2026-11-20T23:55 | `reduction/filter/summary.json` | Committed R3 and the source-position record. |
| 2026-11-20T23:55 | `results/compare/PLAN.md` | The comparison plan, read before any comparison code. |
| 2026-11-20T23:56 | `results/compare/DIGITISE.md` | Column definitions the plan points to. The “What to write” section. |
| 2026-11-20T23:56 | `results/compare/digitised/ai-grok-4.7-2026-11-20/points.csv` | Vector reading of Fig. 3. |
| 2026-11-20T23:56 | `results/compare/digitised/ai-grok-4.7-2026-11-20/digitisation.json` | Axis range for the digitisation floor. |
| 2026-11-20T23:56 | `results/compare/digitised/ay/points.csv` | Second digitisation. |
| 2026-11-20T23:56 | `results/compare/digitised/ay/digitisation.json` | Axis range and method of the second reading. |
| 2026-11-20T23:57 | `analysis/lightcurves/lightcurves.py` | Imports, and the lines that define the light-curve columns, so the rebuilt spectrum uses the same quantities the plan names. |
| 2026-11-20T23:58 | `labelled_partial_bins.py` and its outputs | A separate copy that fills every bin with `FRACEXP < 1`. Not a change to the phase-1 code. |
| 2026-11-21T00:00 | `compare_own.py` | Own comparison, written from the plan. `results/compare/compare.py` was not opened. |
| 2026-11-21T00:01 | `results/compare/comparison.json` | The explainer’s comparison output, opened only after `compare_own.py` had been run. |
| 2026-11-21T00:02 | own `outputs/comparison_own.json` and `comparison_own.csv` | To set them next to the explainer’s output. |

## Not blind

A search for the result IDs, meant to stay inside the method documents, was
run on the whole tree. It printed lines from the score sheet, the R1 page,
the comparison plan and result, the work log, and the 2026-11-19 re-run
report. Those lines include lag values, a net exposure, and the comparison
outcome category. While preparing the phase-1 commit I also saw the message
of `b5d8b4b`, which quotes the comparison’s summary numbers. None of those
files was opened in phase 1, and nothing in `derive_r1_r3.py` was changed
after those lines appeared. The phase-2 judgement uses `CRITERION.md` as
committed, not a rule adjusted toward those numbers.

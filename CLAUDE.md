# Retrace

Open, reproducible, agent-checkable science, starting with X-ray reverberation in AGN.
Owner: Andy Young (University of Bristol). This file is project memory for any Claude session.
Andy is a co-author of Fabian et al. 2009, the pilot paper. Anything he recalls about how the original
analysis was done is not published information. Use it only as an explicit assumption with the source
"A. Young (F09 co-author), recollection", and keep the reproduction from the public record separable.

## Ethos
- One agent (the *explainer*) does each analysis step and explains what it did and why, so that
  another agent or a human (the *verifier*) can re-run it from a clean clone and check it.
- Every step is a versioned node in a chain of trust: pinned inputs, environment, code, outputs
  (with hashes) and a plain-language explanation. When something upstream changes, everything
  downstream is stale (DVC handles this: `dvc repro`).
- A score sheet records which results have been reproduced and which mistakes were caught, and by whom.
- Challenges ("check requests") are GitHub issues against a specific result.

## Honesty rules (non-negotiable)
- Never tune choices to make results match the published figure. Published values are for
  comparison only, never inputs.
- Never claim something is "verified" or "reproduced" unless a specific check was run; name the check.
- Never drop, shrink or smooth uncertainties to make a plot look better.
- Record every analysis choice that a paper does not specify as an explicit ASSUMPTION, with its
  source (e.g. a follow-up paper), and test sensitivity to it where feasible.
- Report discrepancies plainly. "I don't know" and "this did not reproduce" are acceptable outcomes.
- Keep failed attempts in the log; don't silently overwrite them.

## Conventions
- Python: Andy uses Homebrew Python with a per-project virtual environment. In Andy's checkout the
  venv IS the repo root (`source bin/activate`; `bin/ include/ lib/ share/ pyvenv.cfg` are git-ignored).
  Fresh clones may use `.venv` instead (also ignored). Install with pip from `requirements.txt`, and record
  exact versions with `pip freeze > requirements.lock`. Never install into the global Homebrew Python.
  Core packages: numpy, scipy, astropy, stingray, matplotlib, pyyaml. DVC comes from Homebrew
  (`brew install dvc`, includes https/s3), not from the venv.
- Pipeline in DVC: stages in `dvc.yaml`, parameters in `params.yaml`, lockfile `dvc.lock` committed.
- Raw data are NOT stored by us: reference HEASARC (`https://nasa-heasarc.s3.amazonaws.com/...`)
  with `dvc import-url` so the URL and checksum are recorded.
- Each stage writes `EXPLAIN.md` next to its outputs: what was done, why, assumptions, checks run.
- Compare FITS products by the content of their data columns, not file bytes (headers carry
  timestamps; some reduction tasks randomise within instrument bins). Stages that write FITS files
  record column hashes with `tools/fits_hashes.py` in a git-tracked `content_hashes.json`.
- Separate facts (measured lags, fluxes) from interpretation (e.g. coronal height under a lamppost model).
- Git: Andy pushes to GitHub himself unless he says otherwise (public repo: github.com/phajy/Retrace).
  DVC remote: local folder only for the pilot; verifiers re-download raw data from HEASARC. Cloudflare R2
  (free tier, Standard class) maybe later.
- Licences: software MIT (`LICENSE`); text, figures, tables and data products CC BY 4.0 (`LICENSE-docs`).
  Don't copy published figures or paper text into the repo; cite them (digitised values with a reference are fine).

## Checking workflow (full description: `docs/METHODOLOGY.md`)
- Results have IDs (R1, R2, …), a page in `results/` and a row in `results/SCORESHEET.md`. Use the check
  names from the methodology (re-run, re-derived, compared). Change the score sheet only for checks that
  were actually run, and name them.
- Result pages quote numbers copied by hand, with the output checksums they came from. Whenever outputs
  change, update the page and its provenance line.
- Check requests, questions and verification reports are GitHub issues (forms in `.github/ISSUE_TEMPLATE/`,
  labels in `.github/labels.sh`). Answer with a commit hash, numbers and a link to a committed figure.
  Post to GitHub only with Andy's go-ahead.
- Plots shown on GitHub pages come from the `figures` DVC stage (`results/figures/`); never copy them by hand.
- A verifier works from a clean clone and the written record only, never from an explainer's session.

## Layout (monorepo for the pilot; split later along reuse lines)
- `docs/`      specs and notes (start with `docs/pilot-1h0707-lags.md`)
- `reduction/` per-observation data reduction stages
- `analysis/`  timing analysis (light curves, cross-spectra, lags)
- `results/`   final tables/figures, comparison with the literature, score sheet
- `verification/` independent re-runs and their reports

## Current task
Pilot: reproduce the lag–frequency spectrum of 1H 0707–495 from Fabian et al. 2009 (Fig. 3).
Full spec: `docs/pilot-1h0707-lags.md`.
Status and next steps: `README.md` (stage table), `docs/LOG.md` (what happened), `docs/assumptions.md`
(every unspecified choice, with IDs used in `params.yaml`), and each stage's `EXPLAIN.md`.

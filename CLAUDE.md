# Retrace

Open, reproducible, agent-checkable science, starting with X-ray reverberation in AGN.
Owner: Andy Young (University of Bristol). This file is project memory for any Claude session.

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
  timestamps; some reduction tasks randomise within instrument bins).
- Separate facts (measured lags, fluxes) from interpretation (e.g. coronal height under a lamppost model).
- Git: Andy pushes to GitHub himself unless he says otherwise. DVC remote: local folder first,
  Cloudflare R2 (free tier, Standard class) later.
- Licences: software MIT (`LICENSE`); text, figures, tables and data products CC BY 4.0 (`LICENSE-docs`).
  Don't copy published figures or paper text into the repo; cite them (digitised values with a reference are fine).

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

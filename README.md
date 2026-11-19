# Retrace

Open, reproducible, agent-checkable science. Pilot: reproduce the lag–frequency spectrum of the
active galaxy 1H 0707–495 from Fabian et al. 2009 (Nature 459, 540; Fig. 3) using public
XMM-Newton data. See `CLAUDE.md` for the ethos and rules, `docs/pilot-1h0707-lags.md` for the spec,
and `docs/assumptions.md` for every choice the paper does not specify.

## Status
| Stage | Where | State |
|---|---|---|
| 1 fetch | `reduction/raw/` (`dvc import-url` records) | done |
| 2 filter | `reduction/filter/` | done (v0: PPS event lists + Python, no SAS) |
| 3 lightcurves | `analysis/lightcurves/` | done |
| 4 lags | `analysis/lags/` | done (baseline); sensitivity tests pending |
| 5 compare | `results/` | not started (needs digitised Fig. 3 points) |
| 6 report | `results/` | not started |
| verification | `verification/` | not started |

Current baseline figure: `analysis/lags/lag_frequency.png`. Read `analysis/lags/EXPLAIN.md` before quoting
any number from it.

## Reproduce from a clean clone
Requirements: git, DVC ≥ 3 with https support (`brew install dvc`), Python 3 (tested with Homebrew Python 3.15.2).

```bash
python3 -m venv .venv && source .venv/bin/activate   # or any venv outside git
pip install -r requirements.lock
dvc update -R reduction/raw   # re-download the raw data from HEASARC, or `dvc pull` from a remote
git diff --stat reduction/raw # must be empty: the md5s of the downloads match the recorded ones
dvc repro                     # filter -> lightcurves -> lags
dvc metrics show              # summary numbers
```
Each stage writes a `summary.json` (in git) and writes its data products to an `output/` folder tracked by DVC.
FITS products should be compared by **data-column content**, not file bytes. Use `reduction/filter/output/content_hashes.json`.

## Environment used for the explainer run (2026-11-19)
macOS 26.7 (arm64), Homebrew Python 3.15.2, DVC 3.67.1 (Homebrew), packages as in `requirements.lock`
(numpy 2.5.5, astropy 8.0.3, stingray 2.3.2, scipy 1.18.1, matplotlib 3.11.2).

## Licence
* **Software: MIT** ([`LICENSE`](LICENSE)). Covers the Python and shell scripts, `dvc.yaml`, `params.yaml` and the
  `requirements*` files.
* **Everything else made in this project: CC BY 4.0** ([`LICENSE-docs`](LICENSE-docs)). Covers the text (every `*.md`,
  including the `EXPLAIN.md` files), figures, tables, `summary.json` files and the DVC-tracked data products.
* **Not covered (not ours):** the XMM-Newton observations (ESA; fetched from HEASARC, not stored here) and the
  published papers and figures we compare against (cited, not copied).

# Score sheet

Records which results have been **reproduced** (by a named check, from a clean clone) and which
mistakes were caught, and by whom. An entry is only "reproduced" once a verifier has re-run it.

## Results
| Result | Explainer status | Verified by | Check | Outcome |
|---|---|---|---|---|
| F09 Fig. 3: lag–frequency spectrum, 0.3–1 vs 1–4 keV | baseline computed 2026-11-19 (`analysis/lags/`); not yet compared bin by bin | — | — | pending |
| F09 SI: mean lag > 7e-4 Hz, 0.5–1 vs 3–7 keV = −6 ± 18 s | not started | — | — | pending |
| F09 SI: 330 ks net pn exposure after flare filtering | 328.6 ks with a pre-chosen 0.4 c/s screen (definition of "net" unknown) | — | — | comparison only |

## Mistakes caught
| Date | What | Caught by | How | Fixed in |
|---|---|---|---|---|
| 2026-11-19 | Venv-generated `.gitignore` (`*`) would have excluded the whole project from git | explainer (Claude) | inspected before `git init` | session 1 |
| 2026-11-19 | Red-noise self-test was too strict (method has a real ~8% leakage bias) | explainer (Claude) | stage failed; diagnosed with white vs red noise | session 1 (see `docs/LOG.md`) |
| 2026-11-19 | Analytic lag errors invalid at the coherence noise floor | explainer (Claude) | inspection of first results | session 1 (A-13, post hoc) |

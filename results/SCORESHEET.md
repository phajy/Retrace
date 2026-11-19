# Score sheet

Which results have been checked, by which check, by whom, and which mistakes were caught.
The checks are defined in [How Retrace works](../docs/METHODOLOGY.md#levels-of-checking).
An entry changes only when a named check has actually been run, and the commit that changes it says which.

## Results
| ID | Result (published value) | Explainer | Re-run | Re-derived | Compared | Challenges |
|---|---|---|---|---|---|---|
| [R1](R1-lag-frequency.md) | F09 Fig. 3: lag–frequency spectrum, 0.3–1 vs 1–4 keV (soft lags hard by "about 30 s" above ~0.6 mHz) | baseline computed 2026-11-19 | not yet | not yet | not yet (needs digitised Fig. 3) | none yet |
| R2 | F09 SI: mean lag above 7×10⁻⁴ Hz, 0.5–1 vs 3–7 keV (−6 ± 18 s) | not started | — | — | — | — |
| R3 | F09: 330 ks net pn exposure after flare filtering | 328.6 ks with a 0.4 c/s screen chosen in advance (F09's definition of "net" is unknown) | not yet | — | comparison only | — |

F09 = Fabian et al. 2009, *Nature* 459, 540 (arXiv:0905.4383). SI = its Supplementary Information.

## Verifications
| Date | Result | Check | Verifier (human, or model and tool) | Commit | Outcome | Report |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Mistakes caught
| Date | What | Caught by | How | Fixed in |
|---|---|---|---|---|
| 2026-11-19 | Venv-generated `.gitignore` (`*`) would have excluded the whole project from git | explainer (Claude) | inspected before `git init` | session 1 |
| 2026-11-19 | Red-noise self-test was too strict (the method has a real ~8% leakage bias) | explainer (Claude) | stage failed; diagnosed with white vs red noise | session 1 (see [`LOG.md`](../docs/LOG.md)) |
| 2026-11-19 | Analytic lag errors invalid at the coherence noise floor | explainer (Claude) | inspection of first results | session 1 (A-13, post hoc) |
| 2026-11-19 | Reference FITS column hashes were inside a DVC-only folder, so a verifier on a fresh clone had nothing to compare against; light-curve FITS had no hashes | explainer (Claude) | noticed while writing the verifier's instructions | session 1 (`tools/fits_hashes.py`; hashes now in git) |

## Planted-mistake tests
Deliberate errors introduced to test whether verifiers catch them (see
[Independence and its limits](../docs/METHODOLOGY.md#independence-and-its-limits)). Recorded here only after the verifier has reported.

| Date | Planted error | Verifier | Caught? | Notes |
|---|---|---|---|---|
| — | — | — | — | — |

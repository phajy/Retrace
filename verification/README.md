# Verification reports

Independent checks of the results, one folder per verification:
`verification/<YYYY-MM-DD>-<who>/REPORT.md`, for example `2026-11-20-claude-sonnet/REPORT.md`.

The check types (re-run, re-derived, compared) are defined in
[How Retrace works](../docs/METHODOLOGY.md#levels-of-checking).

## Rules for verifiers
* AI verifiers are started with the generic [prompt](PROMPT.md), pasted unchanged with only its three fields
  filled in (the commit, the tasks, the verifier's model and tool). Human verifiers can follow it too.
* Start from a **clean clone** of a named commit, not from the explainer's working copy.
* Start in a **new session or workspace** with no earlier history of this project. If you have seen any of the
  project's results before, for example in an earlier check, you are not blind to them: say so in the report.
* Use only the **written record**: the README, the `EXPLAIN.md` files, `docs/assumptions.md` and the code.
  You do not see the explainer's conversation.
* For a **re-derivation**, write your own code from the written method *before* reading the explainer's
  code for that step. Say in the report what you read and when.
* Compare outputs by checksum (`dvc.lock`) or, for FITS files, by data-column content, not by file bytes.
  The committed reference hashes are in `reduction/filter/content_hashes.json` and
  `analysis/lightcurves/content_hashes.json`. `dvc repro` regenerates both, so `git diff` shows any
  difference, and `tools/fits_hashes.py` recomputes them for any FITS file.
* Report what happened plainly, including steps that failed or instructions that were unclear.
  A report that says "the README instructions did not work" is a useful result.

## What a report contains
1. Result(s) and check type, the commit checked, the date, who you are (human, or model and tool).
2. What you had access to, and whether you had seen any of the project's results before (where and when).
3. Environment (OS, Python, DVC, package versions).
4. Exactly what you ran.
5. What you compared and what you found, with numbers.
6. Outcome: matches, differs, or could not complete.

Then open a *Verification report* issue that links to the report. If you were told not to post (agents
in this proof of concept usually are), the maintainer opens the issue and the pull request for you from
the report. The maintainer updates the [score sheet](../results/SCORESHEET.md).

## Reports so far
| Date | Verifier | Check | Commit | Outcome | Report |
|---|---|---|---|---|---|
| 2026-11-19 | Grok 4.7 High Fast in Cursor | re-run of R1 and R3 | `9eea9a1` | matches | [REPORT.md](2026-11-19-grok-4.7-high-fast/REPORT.md), [#2](https://github.com/phajy/Retrace/issues/2) |
| 2026-11-20 | Grok 4.7 High Fast in Cursor | re-derivation of R1 and R3; comparison of R1 with F09, own code from the plan | `9cb723d` | R3 matches; R1 differs (0.10–0.16σ in two bins and the high-frequency mean); comparison matches | [REPORT.md](2026-11-20-grok-4.7/REPORT.md), [#6](https://github.com/phajy/Retrace/issues/6) |

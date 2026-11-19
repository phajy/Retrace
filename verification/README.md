# Verification reports

Independent checks of the results, one folder per verification:
`verification/<YYYY-MM-DD>-<who>/REPORT.md`, for example `2026-11-20-claude-sonnet/REPORT.md`.

The check types (re-run, re-derived, compared) are defined in
[How Retrace works](../docs/METHODOLOGY.md#levels-of-checking).

## Rules for verifiers
* Start from a **clean clone** of a named commit, not from the explainer's working copy.
* Use only the **written record**: the README, the `EXPLAIN.md` files, `docs/assumptions.md` and the code.
  You do not see the explainer's conversation.
* For a **re-derivation**, write your own code from the written method *before* reading the explainer's
  code for that step. Say in the report what you read and when.
* Compare outputs by checksum (`dvc.lock`) or, for FITS files, by data-column content
  (`reduction/filter/output/content_hashes.json`), not by file bytes.
* Report what happened plainly, including steps that failed or instructions that were unclear.
  A report that says "the README instructions did not work" is a useful result.

## What a report contains
1. Result(s) and check type, the commit checked, the date, who you are (human, or model and tool).
2. What you had access to.
3. Environment (OS, Python, DVC, package versions).
4. Exactly what you ran.
5. What you compared and what you found, with numbers.
6. Outcome: matches, differs, or could not complete.

Then open a *Verification report* issue that links to the report. The maintainer updates the
[score sheet](../results/SCORESHEET.md).

## Reports so far
None yet.

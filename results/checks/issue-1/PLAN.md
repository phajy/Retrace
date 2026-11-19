# Check request #1: plan, fixed before running

Issue: https://github.com/phajy/Retrace/issues/1 ("[Check] R1: background flares", opened by a human challenger).
Commit checked: `9eea9a1`. Explainer: Claude Opus 5.5 in Claude Code.

**Reading of "leaving in the flares".** The baseline already includes the flaring intervals in the 0301 and
0401 windows, but subtracts the scaled background (assumption A-08). Leaving the flares in therefore means
switching that subtraction off:

```bash
dvc exp run -n issue-1-no-bkg-subtraction -S lags.background_subtract=false
```

Everything else is as at `9eea9a1`. This keeps the whole background, flares included, in both bands. If the
lags barely change even then, the leftover after subtraction can't matter much either. That leftover should
be much smaller, unless the background scaling is wrong by more than a factor of 2.

**What will be compared** (baseline vs test, from `summary.json` and `lag_frequency.csv`):
1. Weighted mean lag over the reliable bins in 0.7–5 mHz (baseline −16.8 ± 3.4 s).
2. Weighted mean lag over the reliable bins in 0.1–0.5 mHz (baseline +81 ± 15 s).
3. Frequency where the lag changes sign (baseline 5.9×10⁻⁴ Hz).
4. Most negative reliable bin (baseline −31.7 ± 8.1 s at 1.34×10⁻³ Hz).
5. The lag in every frequency bin, and which bins count as reliable.

**What counts as a significant change** (our operational reading of "significantly"). Any of:
* item 1 or 2 moves by more than the baseline's 1σ error;
* item 3 moves to a different pair of frequency bins;
* any bin that is reliable in both runs moves by more than its baseline 1σ error.

This is a strict test. Both runs use the same source photons, so their errors are strongly correlated, and
a real difference shows up well below a naive combined error.

**Outcomes.**
* No significant change: `outcome: confirmed`. The background, flares included, does not affect R1 at this level.
* Significant change: as the request says, think more carefully. `outcome: inconclusive` for now, plus a
  follow-up check with flare-free windows (shorter windows that end before the flares), which tests the
  leftover after subtraction directly.
* Either way, the baseline stays as it is unless a follow-up gives a reason, stated in advance, to change it.

Results will go in this folder (numbers and a comparison figure) and be linked from the issue with the commit.

# Match criterion for the re-derivation of R1 and R3

Written before any comparison with the explainer's code or outputs. This is the
rule for phase 2. It will not be edited after that comparison starts.

The data are the same archive files, and both analyses are deterministic, so a
shared reading of the method should agree much more closely than the statistical
error bars. The bars are still the scale used below, because that is the
uncertainty the method itself reports.

## R3, net exposure

R3 here is the sum, over the four included exposures, of the time that is both
inside a flare-good 100 s bin (full-field rate strictly below 0.4 counts/s) and
inside the CCD-4 standard GTIs.

**Match:** the absolute difference from the explainer's R3 is at most one flare
bin, 100 seconds.

**Differs:** the absolute difference is greater than 100 seconds.

## R1, lag–frequency spectrum

The sign self-test in `derive_r1_r3.py` is a check of this implementation only.
It has to recover a positive lag within 1 second of +30 s, which is the
tolerance stated in the lag-stage method. It is not part of the comparison.

**Match**, all of the following:

1. Frequency edges agree, bin by bin, to a relative tolerance of 10⁻⁶. If they
   do not, because the written record never states the frequency of the first
   edge, both spectra are compared after averaging onto the explainer's edges
   with the same mean of the complex cross spectrum. That edge mismatch is then
   recorded as a gap in the record, and it is not by itself a failed match.
   Any other edge mismatch is a difference.
2. The same bins are flagged reliable.
3. On every bin that both flag as reliable, the absolute lag difference is less
   than 10% of the larger of the two 1σ errors.
4. The inverse-variance mean of reliable lags with mean frequency in
   [7×10⁻⁴, 5×10⁻³) Hz differs by less than 10% of the larger of the two
   uncertainties on that mean.

**Differs:** any of 2–4 fails, or an edge mismatch that is not the unspecified
first edge.

Every numerical difference is reported either way, including differences inside
these bounds.

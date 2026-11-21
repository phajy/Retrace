# Phase 1 record

Written before any comparison with the explainer's code or committed outputs.

At 12:15 UTC another process changed the original worktree, made a commit, and
created phase-2 files in this verification folder. I did not open those files.
To preserve the phase boundary, I created this isolated worktree and branch
directly from `d104bc4`, copied only the phase-1 files I had authored, fetched
the pinned raw inputs again, and repeated the phase-1 run here.

## Scope inferred from the permitted record

`dvc.yaml` makes `filter -> lightcurves -> lags` the dependency chain from the raw
archive files to the lag-frequency result. The permitted record identifies R1 as the
lag-frequency spectrum but does not map the label R3 to a particular lag-stage
quantity. I therefore independently derived the full lag table, reliability flags,
and the 0.7–5 mHz inverse-variance weighted mean so that R3 can be identified after
unblinding without changing the calculation.

## Independent implementation

`derive.py` reads the four included PPS event lists directly and does not import or
run Retrace pipeline code. It uses Python 3.15.2, NumPy, Astropy, PyYAML and Stingray.
It performs the written event cuts, region construction, light-curve binning, window
selection, gap interpolation, Fourier calculation, geometric frequency binning,
coherence calculation, reliability test and high-frequency weighted mean.

## Assumptions needed to turn the written method into code

1. Convert `RA_OBJ`/`DEC_OBJ` to event-list X/Y using Astropy spherical offsets from
   the FITS tangent-point reference. Iterative centroids are arithmetic X/Y means.
2. Fit the CCD-4 X/Y-to-RAW affine map by unweighted least squares over all CCD-4
   events. Map the source centre to RAW, subtract 25 from RAWX, then invert the fit
   to obtain the background X/Y centre.
3. Treat circular-region boundaries as excluded. Energy bands and time bins are
   half-open: `[low, high)`.
4. Anchor both 10 s light-curve bins and 100 s flare bins at the first `STDGTI04`
   start. Extend the regular grid to the first edge at or after the last GTI stop.
5. Define each quiet flare bin by `counts / 100 s < 0.4 counts/s`, then intersect
   those bins with `STDGTI04`.
6. Consider 100 ks window starts only on the 10 s grid, require the first and last
   bins to be fully exposed, reject windows containing a gap run longer than 200 s,
   maximise summed flare-GTI fractional exposure, and choose the earliest exact tie.
7. Use background area ratio 1.0, as the written method says both effective areas
   are equal to the shown precision.
8. Call Stingray `intrinsic_coherence` with `adjust_bias=True`, because the written
   method explicitly says the Ingram (2019) bias term is used.
9. Include a bin in the high-frequency mean when its mean Fourier frequency is in
   `[7e-4, 5e-3)` Hz and its reliability flag is true.

## Match criterion fixed before comparison

Because this is the same raw data and a specified deterministic calculation, matching
means:

* identical frequency-bin count, Fourier-frequency membership (`n_frequency`) and
  reliability flag in every bin;
* for R1, every reliable-bin lag differs by no more than 0.10 times the explainer's
  quoted 1-sigma lag error, and every reliable-bin lag error differs by no more than
  1%; and
* for any R3 scalar summary, the same contributing reliable bins and a value differing
  by no more than 0.10 times its quoted 1-sigma uncertainty.

Differences outside any threshold count as a differing result, even if scientifically
small. Intermediate event counts, selected windows and noise levels will also be
reported numerically, but they are diagnostics rather than additional pass criteria.
# Phase 1: independent derivation record

## Scope and independence

I am re-deriving R1 and R3 from the raw HEASARC PPS event lists. I wrote
`derive.py` without reading the explainer's pipeline code, committed output tables,
summaries, figures, `dvc.lock`, `docs/LOG.md`, or result pages.

The allowed method record disclosed two prior-check facts before I wrote the code:

1. `verification/README.md` says an earlier re-derivation found 0.10–0.16 sigma
   differences in two R1 bins and the high-frequency mean.
2. `docs/assumptions.md` and `analysis/lags/EXPLAIN.md` say those differences arose
   because that verifier retained partly exposed bins. They also disclose the
   explainer's gap counts and several diagnostic values.

I did not use those values as targets. In particular, `derive.py` implements the
written rule that every `FRACEXP < 1` bin is a gap and interpolates it.

## Libraries

Python 3.15.2; NumPy 2.5.5; SciPy 1.18.1; Astropy 8.0.3; PyYAML 6.0.4;
Matplotlib 3.11.2. The derivation uses NumPy, Astropy, PyYAML and Matplotlib; it
does not use Stingray or any project pipeline module.

## Assumptions and independent choices

1. The task names R1 and R3 but the permitted phase-1 material does not define the
   result IDs without entering a skipped Results section or a result page. I
   therefore derive the complete lag-frequency table and its inverse-variance
   weighted 0.7–5 mHz reliable-bin mean, which are the lag-stage products described
   by the method.
2. A sky-coordinate unit in the event-list `X`/`Y` columns is taken from
   `REFXCDLT`/`REFYCDLT` (0.05 arcsec). The source centroid is an unweighted event
   centroid iterated to convergence.
3. The CCD-4 RAW-to-sky relation is fitted as an affine map using every tenth
   eligible event. The background centre is the inverse-mapped source centre minus
   25 RAWX pixels at the same RAWY, then mapped back to sky coordinates.
4. Source and background circular cuts are made in event-list sky coordinates.
   `BACKRAT` is 1.0 as stated by the method.
5. Light-curve bins start at the first CCD-4 standard-GTI start. The final grid
   extends by whole 10 s bins through the final CCD-4 standard-GTI stop.
6. Flare-screen 100 s bins start at the event header's `TSTART`. A flare bin is
   accepted when its rate is strictly below 0.4 count/s, matching “below” in the
   written method. Window cost is the summed fractional time outside accepted
   flare bins.
7. Candidate 100 ks windows begin on the 10 s light-curve grid. They must begin and
   end in fully exposed bins and contain no internal gap run longer than 200 s.
   The earliest minimum-cost candidate is selected.
8. `FRACEXP >= 1 - 1e-9` counts as fully exposed, to tolerate floating-point
   interval arithmetic. All other bins are replaced by linear interpolation in
   each net light curve.
9. Cross spectra use `conj(H) * S`, no FFT normalization, a rectangular window and
   mean-subtracted 100 ks segments. Noise uses the mean fully-exposed per-bin
   source-plus-background variance times 10,000 bins.
10. Intrinsic coherence uses the Vaughan–Nowak noise-bias expression. A bin is
    defined when each signal power exceeds its noise by more than
    `3 * noise / sqrt(K)`, as stated in the method; reliability additionally
    requires `K >= 30`.
11. No raw archive file, FITS product or large intermediate will be committed.

## Match criterion fixed before phase-2 comparison

Because both implementations use the same raw files and the written method is
numerically specific, R1/R3 will count as a match only if:

* the same 25 frequency bins are present and the same bins are marked reliable;
* every reliable-bin lag differs by at most 0.05 of the explainer's quoted
  1-sigma lag error;
* the inverse-variance weighted 0.7–5 mHz lag differs by at most 0.05 of the
  explainer's quoted 1-sigma error; and
* sign conventions and the qualitative high-frequency sign agree.

I will still report every numerical difference, including those below this
threshold. If a discrepancy is due to an ambiguity in the written method rather
than an implementation mistake, the first phase-1 output remains the outcome
being judged.

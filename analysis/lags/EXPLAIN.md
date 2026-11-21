# Stage 4 — lags (cross-spectrum, lag–frequency spectrum, coherence)

Script: `lags.py` · parameters: `exposures`, `lightcurves`, `lags` · numbers: `summary.json`
· table: `lag_frequency.csv` · figure: `lag_frequency.png` · unbinned spectra: `output/` (DVC-tracked).

## Sign convention (stated in every output)
**lag > 0: the hard band (1–4 keV) lags the soft band (0.3–1 keV). lag < 0: soft lags hard.**
This is the convention of F09 Fig. 3 ("negative lag … indicates the harder flux … changing before
the softer flux"), Z10 and K13. It is computed as lag(f) = arg⟨H*(f) S(f)⟩ / 2πf with numpy's FFT, and
**checked on every run** by a synthetic pair with the hard band delayed by +30 s (see Checks).

## What was done and why
* **Background-subtracted** light curves, net = src − BACKRAT × bkg (A-08, Z10).
* **Segments** (A-09): one **100 ks** window per orbit (4 segments), following Z10 ("4 segments of about
  100 ks"). The flare-screened GTIs from the filter stage are too fragmented (longest 7.6–35 ks) to
  reach the ~1e-5 Hz frequencies of F09 Fig. 3. Windows are placed to minimise time outside the
  flare-screen GTIs. Only 0101 (121.6 ks) has any freedom: its window starts 4.1 ks in, avoiding the opening flare.
  The other exposures are 101.8–104.0 ks long, so their windows include most of their flaring periods
  (time outside the flare GTIs: 0.8, 23.7, 31.4, 26.6 ks for 0101, 0201, 0301, 0401).
* **Gaps** (A-10). Stated precisely on 2026-11-21 after the verifier's report ([#6](https://github.com/phajy/Retrace/issues/6)); the method is unchanged.
  * A 10 s bin is a **gap** if it is not entirely inside the CCD-4 standard GTIs (`FRACEXP` < 1). So partly exposed
    bins are gaps too, and their recorded counts are not used.
  * Inside a window, the net counts of every gap bin are replaced by linear interpolation between the nearest fully
    exposed bins (`numpy.interp`), with no added noise. If a window began or ended inside a gap, those bins would take
    the value of the nearest fully exposed bin; this does not happen in the baseline.
  * A window can contain only runs of gap bins at most `max_gap_fill_s` = 200 s (20 bins) long, with fully exposed
    bins on both sides. A longer gap ends the stretch in which a window can be placed.
  * In the baseline the four windows have 11, 6, 2 and 3 gap bins. That is a result, not part of the rule: 5, 5, 2
    and 3 of them are partly exposed, and 6, 1, 0 and 0 have no exposure at all.
  * Keeping the counts of partly exposed bins instead, as the verifier's phase 1 code did, moves two reliable bins and
    the 0.7–5 mHz mean by 0.10–0.16σ ([#6](https://github.com/phajy/Retrace/issues/6)).
* For each segment: subtract the mean, rectangular window, numpy `rfft`. Average C = H*S, |S|², |H|²
  over the 4 segments, then over geometric frequency bins with f_hi = 1.4 f_lo (A-11). Stated precisely on
  2026-11-21 after the verifier's report ([#6](https://github.com/phajy/Retrace/issues/6)); the method is unchanged:
  * The Fourier frequencies are j/T for j = 1 to 4999 (T = 100 ks, so 10⁻⁵ to 0.04999 Hz). The zero frequency and
    the Nyquist frequency (0.05 Hz) are dropped.
  * The first edge is just below the lowest Fourier frequency, at 10⁻⁵ × (1 − 10⁻⁹) Hz, so that 10⁻⁵ Hz falls
    inside the first bin despite rounding. Each further edge is 1.4 times the one before, up to the first edge at or
    above the highest Fourier frequency. So the last bin (0.0450–0.0630 Hz) is kept, although it holds only the
    frequencies up to 0.04999 Hz.
  * A frequency on an edge belongs to the upper bin (f_lo ≤ f < f_hi). A bin with no Fourier frequency is skipped
    (one: 1.4–1.96×10⁻⁵ Hz), which leaves 25 bins.
  * The lag of a bin is its phase divided by 2π times the mean of its Fourier frequencies (`f_mean_hz`).
* **Lag error**: Nowak et al. 1999 eq. 16 with the raw coherence, K = 4 × (Fourier frequencies in the bin)
  (A-12). **Coherence**: raw |⟨C⟩|²/(⟨|S|²⟩⟨|H|²⟩), plus the intrinsic coherence and its error from
  `stingray.fourier.intrinsic_coherence` (Vaughan & Nowak 1997 eq. 8; bias term from Ingram 2019).
  The **Poisson noise level** N of each band is the expected |rfft|² of the counting noise, in the units of this
  unnormalised FFT. For each window, it is the mean per-bin variance (src + BACKRAT² × bkg, in counts) of the fully
  exposed bins, times the number of bins in the window (10 000), so interpolated bins are given that mean variance.
  N is then averaged over the four windows. It is 3.6×10⁻⁴ (soft) and 3.8×10⁻⁴ (hard) higher than the plain sum of
  the recorded per-bin variances. Until 2026-11-21 this file said "the summed per-bin variance", and a code comment
  in `lags.py` still does (found by the verifier, [#6](https://github.com/phajy/Retrace/issues/6)). The comment will be corrected with the next real change to
  this stage, together with the line endings below.
* **Reliability flag** (A-13, *added after the first run, post hoc*): a bin counts as reliable only if
  its intrinsic coherence is defined (powers more than 3σ above the noise) and K ≥ 30. In the first run the analytic
  errors were visibly invalid at the noise floor (e.g. "−12.9 ± 1.6 s" at 39 mHz, γ²_raw ≈ 6e-4).
  Unreliable bins are kept in the CSV (column `reliable` = 0) and shown as open grey symbols.

## Results (facts; baseline parameters; see `summary.json` and `lag_frequency.csv`)
* Reliable bins span 2.45e-4 – 3.66e-3 Hz.
* Lags are positive (hard lags soft) at low frequency: +211 ± 32 s at 2.45e-4 Hz and +91 ± 29 s at 3.45e-4 Hz.
  The weighted mean over the reliable bins in 1e-4–5e-4 Hz is **+81 ± 15 s** (3 bins). Below 2.45e-4 Hz all
  bins are flagged (K < 30). Between 6.5e-5 and 1.75e-4 Hz their point estimates are +106 to +163 s (errors 53–170 s).
  The lowest four bins (1e-5 to 4.5e-5 Hz, K = 4–8) scatter from −1333 to +453 s (errors 200–1200 s).
* The lag changes sign (positive → negative) at **5.9e-4 Hz** (log-linear interpolation between bins).
* Lags are negative (soft lags hard) from 6.8e-4 to 3.7e-3 Hz. The most negative reliable bin is
  **−31.7 ± 8.1 s at 1.34e-3 Hz**. The weighted mean over the reliable bins in 7e-4–5e-3 Hz is **−16.8 ± 3.4 s** (5 bins).
* The intrinsic coherence is 0.72–0.98 from 1e-5 to 2.6e-3 Hz and 0.55 ± 0.15 at 3.7e-3 Hz. Above ~4e-3 Hz
  the powers are too close to the Poisson noise for the coherence to be defined.

## Raw and intrinsic coherence, in plain language (added for [question #4](https://github.com/phajy/Retrace/issues/4))
Both measure how closely the two bands vary together at a given frequency: 1 means one band is a delayed,
rescaled copy of the other, 0 means they are unrelated.
* The **raw** coherence uses the measured spectra, which include Poisson counting noise. The noise is independent
  in the two bands, so it lowers the raw coherence wherever it is a large part of the measured power.
* The **intrinsic** coherence subtracts the expected noise first, (|⟨C⟩|² − b²) / ((⟨|S|²⟩ − N_S)(⟨|H|²⟩ − N_H)),
  so it describes the source. Stingray leaves it undefined when either power is less than 3 N/√K above its noise level N.
* They are used for different things. The lag error uses the **raw** coherence (Nowak et al. 1999), because the
  noise also makes the measured phase uncertain. The reliability flag (A-13) uses whether the **intrinsic** coherence is defined.

Facts (from [`results/answers/issue-4/coherence_noise.json`](../../results/answers/issue-4/coherence_noise.json)):
* Below ~3e-4 Hz the source power is 68–4500 times the noise, and the two coherences agree to within 0.02.
* At higher frequencies the raw coherence falls (0.51 at 9.6e-4 Hz, 0.03 at 3.7e-3 Hz), while the intrinsic
  coherence stays at 0.72–0.91 up to 2.6e-3 Hz. The fall of the raw coherence there is mostly counting noise.
* Where the power is only 1.2–3 times the noise (1.3e-3 to 3.7e-3 Hz), the intrinsic coherence depends strongly on
  the noise level. Recomputed with both noise levels 5% lower or higher, it ranges from 0.86 to 0.96 at 1.34e-3 Hz,
  0.68 to 1.02 at 2.6e-3 Hz, and 0.40 to 0.83 at 3.7e-3 Hz. Below 1e-3 Hz it moves by at most 0.016.
* Noise-level check: above 1e-2 Hz, where the source adds little power, the measured power over the predicted noise
  averages 0.98 (soft) and 1.00 (hard), with a range of 0.95–1.03. So the noise level is right to about 2%. The
  intrinsic-coherence error bars (Vaughan & Nowak 1997 eq. 8) assume high powers, so they do not include this.

## Comparison with the publication (descriptive only; written before the formal comparison)
*The formal comparison, the `compare` stage, was run on 2026-11-20: [result](../../results/compare/RESULT.md). This
section was written before it and is kept as it was.*

F09 (text and Fig. 3 caption): positive lags at low frequency; negative above ~0.6 mHz (caption: 7e-4 Hz);
"the soft reflection dominated band follows the hard powerlaw dominated one by about 30 s".
* The **shape and sign** match that description: positive at low frequency, sign change at 5.9e-4 Hz,
  negative above.
* **Magnitude:** our most negative bin (−31.7 ± 8.1 s) is consistent with "about 30 s". The weighted mean
  over 7e-4–5e-3 Hz (−16.8 ± 3.4 s) is smaller in magnitude. We don't know how F09 got "about 30 s"
  (peak or average, and over which range). **This is not yet a reproduction claim.** That needs a
  bin-by-bin comparison with digitised Fig. 3 points and the sensitivity tests below.
* Z10 describes its Fig. 18 as hard lagging soft by "about 150 seconds" below ~5e-4 Hz. Our reliable bins there
  are +91 to +211 s (mean +81 ± 15 s). The comparison is again pending digitisation.

## Checks run (every run; results in `summary.json`)
* **Sign and units self-test:** white-noise pair, hard band delayed by +30 s, 4 × 100 ks of 10 s bins:
  recovered median +29.8 s over 1e-4–3e-3 Hz → **passed** (tolerance 1 s). A sign error would give −30 s.
* **Independent implementation:** Stingray 2.3.2 `AveragedCrossspectrum.from_lc_iterable` on the same
  segments gives the same lag at every Fourier frequency (max |difference| = 4e-13 s) → **passed**.
  The stage exits with an error if either check fails.
* **Red-noise leakage diagnostic (reported, not pass/fail; M-02):** with a steep (∝ f⁻²) PSD and 32
  segments the method recovers 27.7 s for an injected 30 s (ratio 0.92). |Lag| is biased low by leakage.
  F09/Z10/K13 used the same method, so this does not affect the like-for-like comparison, but it matters for interpretation.

### Failed attempt (kept per the honesty rules)
The first version of the self-test used *red-noise* light curves with a 1 s tolerance. It recovered 28.3 s and
the stage failed. Diagnosis (white vs red noise, 4 vs 32 segments) showed a real leakage bias, not scatter
or a sign/unit bug. The pass/fail test now uses white noise, and the red-noise result is reported every run.

## Open concerns and next sensitivity tests (in priority order)
1. **End-of-orbit flares inside the windows.** In 0401 (~78–102 ks) and 0301 (~82–104 ks) the scaled background
   reaches ~1 c/s in 0.3–10 keV, comparable to the source in the hard band. Background subtraction removes it
   to first order, but scaling errors would leave flare variability in the light curves. Tests:
   `timing_gti: flare_gti` (short segments), and shorter or unequal windows that stop before the end-of-orbit flares.
   **Update (check request #1, `results/checks/issue-1/RESULT.md`):** switching background subtraction off, which
   leaves the whole background including the flares in, moves no reliable bin by more than 0.34σ. The flares do
   not affect the result at that level.
2. **PATTERN ≤ 12** for timing (Z10 says patterns were relaxed for timing) — `lightcurves.pattern_max=12`.
3. **Frequency binning factor 2.4** (literal reading of Z10) — `lags.freq_bin_factor=2.4`.
4. No background subtraction; 20 s bins; gap filling by segment mean.
5. Timmer & König simulations with the measured PSD for errors and bias (as in Z10 §5.3).

## Known minor issue (found by a verifier)
`lag_frequency.csv` mixes line endings. The three `#` comment lines end in `\n`, but Python's `csv` writer ends
the column-header and data rows in `\r\n`. No number is affected. It was found during the independent re-run of
2026-11-19 ([#2](https://github.com/phajy/Retrace/issues/2)). The fix (`lineterminator="\n"` in `lags.py`) changes
the file's checksum, so it will be made with the next real change to this stage. The code comment about the Poisson
noise level (above, [#6](https://github.com/phajy/Retrace/issues/6)) will be corrected at the same time.

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
* **Gaps** ≤ 200 s inside a window (11, 6, 2, 3 bins of 10 s) are filled by linear interpolation (A-10).
* For each segment: subtract the mean, rectangular window, numpy `rfft`. Average C = H*S, |S|², |H|²
  over the 4 segments, then over geometric frequency bins with f_hi = 1.4 f_lo (A-11).
* **Lag error**: Nowak et al. 1999 eq. 16 with the raw coherence, K = 4 × (Fourier frequencies in the bin)
  (A-12). **Coherence**: raw |⟨C⟩|²/(⟨|S|²⟩⟨|H|²⟩), plus the intrinsic coherence and its error from
  `stingray.fourier.intrinsic_coherence` (Vaughan & Nowak 1997 eq. 8; bias term from Ingram 2019).
  The Poisson noise level of each band is the summed per-bin variance (src + BACKRAT² × bkg).
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

## Comparison with the publication (descriptive only; the formal comparison is the `compare` stage, not yet built)
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
2. **PATTERN ≤ 12** for timing (Z10 says patterns were relaxed for timing) — `lightcurves.pattern_max=12`.
3. **Frequency binning factor 2.4** (literal reading of Z10) — `lags.freq_bin_factor=2.4`.
4. No background subtraction; 20 s bins; gap filling by segment mean.
5. Timmer & König simulations with the measured PSD for errors and bias (as in Z10 §5.3).

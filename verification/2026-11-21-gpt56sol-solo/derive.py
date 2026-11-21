#!/usr/bin/env python3
"""Independent raw-archive derivation of the Retrace lag-frequency products.

This implementation was written during blinded phase 1 from the permitted
method record.  It does not import or execute project pipeline code.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import yaml
from astropy.coordinates import SkyCoord
from astropy.io import fits
import astropy.units as u
from stingray.fourier import intrinsic_coherence


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PARAMS = yaml.safe_load((ROOT / "params.yaml").read_text())

EVENT_FILES = {
    ("0511580101", "PNS001"): "P0511580101PNS001PIEVLI0000.FTZ",
    ("0511580201", "PNS001"): "P0511580201PNS001PIEVLI0000.FTZ",
    ("0511580301", "PNU002"): "P0511580301PNU002PIEVLI0000.FTZ",
    ("0511580401", "PNU002"): "P0511580401PNU002PIEVLI0000.FTZ",
}


def interval_fraction(edges: np.ndarray, intervals: np.ndarray) -> np.ndarray:
    """Fraction of each regular bin covered by a union of intervals."""
    width = np.diff(edges)
    covered = np.zeros(width.size, dtype=float)
    for start, stop in intervals:
        covered += np.clip(
            np.minimum(edges[1:], stop) - np.maximum(edges[:-1], start),
            0.0,
            width,
        )
    return np.minimum(covered / width, 1.0)


def in_intervals(times: np.ndarray, intervals: np.ndarray) -> np.ndarray:
    """Return whether each time is in any half-open interval."""
    starts = intervals[:, 0]
    stops = intervals[:, 1]
    index = np.searchsorted(starts, times, side="right") - 1
    good = index >= 0
    out = np.zeros(times.size, dtype=bool)
    out[good] = times[good] < stops[index[good]]
    return out


def intersect_intervals(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    intersections: list[tuple[float, float]] = []
    for a0, a1 in left:
        for b0, b1 in right:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                intersections.append((lo, hi))
    return np.asarray(intersections, dtype=float).reshape(-1, 2)


def initial_source_xy(header: fits.Header) -> tuple[float, float]:
    """Project RA_OBJ/DEC_OBJ near the event-list tangent point."""
    reference = SkyCoord(header["REFXCRVL"] * u.deg, header["REFYCRVL"] * u.deg)
    target = SkyCoord(header["RA_OBJ"] * u.deg, header["DEC_OBJ"] * u.deg)
    east, north = reference.spherical_offsets_to(target)
    x = header["REFXCRPX"] + east.to_value(u.deg) / header["REFXCDLT"]
    y = header["REFYCRPX"] + north.to_value(u.deg) / header["REFYCDLT"]
    return float(x), float(y)


def affine_background_center(
    x: np.ndarray,
    y: np.ndarray,
    rawx: np.ndarray,
    rawy: np.ndarray,
    ccd: np.ndarray,
    source_xy: tuple[float, float],
) -> tuple[float, float, tuple[float, float]]:
    """Use an affine sky-to-RAW fit, then offset the source by -25 RAWX."""
    use = ccd == 4
    # Centering avoids conditioning problems from X/Y values near 26000.
    x0 = float(np.mean(x[use]))
    y0 = float(np.mean(y[use]))
    design = np.column_stack(
        [np.ones(np.count_nonzero(use)), x[use] - x0, y[use] - y0]
    )
    coefficients = np.linalg.lstsq(
        design,
        np.column_stack([rawx[use], rawy[use]]),
        rcond=None,
    )[0]
    source_design = np.array(
        [1.0, source_xy[0] - x0, source_xy[1] - y0]
    )
    source_raw = source_design @ coefficients
    background_raw = source_raw + np.array([-25.0, 0.0])
    background_xy_offset = np.linalg.solve(
        coefficients[1:, :].T,
        background_raw - coefficients[0, :],
    )
    background_xy = background_xy_offset + np.array([x0, y0])
    return (
        float(background_xy[0]),
        float(background_xy[1]),
        (float(source_raw[0]), float(source_raw[1])),
    )


def longest_false_run(valid: np.ndarray) -> int:
    padded = np.concatenate(([True], valid, [True]))
    boundaries = np.flatnonzero(padded)
    return int(np.max(np.diff(boundaries) - 1, initial=0))


def choose_window(
    fully_exposed: np.ndarray,
    flare_fraction: np.ndarray,
    window_bins: int,
    max_gap_bins: int,
) -> tuple[int, float]:
    """Choose the earliest best 100 ks grid window allowed by the method."""
    candidates: list[tuple[float, int]] = []
    for start in range(0, fully_exposed.size - window_bins + 1):
        stop = start + window_bins
        valid = fully_exposed[start:stop]
        if not valid[0] or not valid[-1]:
            continue
        if longest_false_run(valid) > max_gap_bins:
            continue
        candidates.append((float(np.sum(flare_fraction[start:stop])), start))
    if not candidates:
        raise RuntimeError("No valid 100 ks window")
    best_coverage = max(item[0] for item in candidates)
    best_start = min(start for coverage, start in candidates if coverage == best_coverage)
    return best_start, best_coverage


def process_exposure(obsid: str, expo: str) -> tuple[dict[str, np.ndarray], dict]:
    cfg_filter = PARAMS["filter"]
    cfg_lc = PARAMS["lightcurves"]
    cfg_lag = PARAMS["lags"]
    path = ROOT / "reduction" / "raw" / obsid / EVENT_FILES[(obsid, expo)]

    with fits.open(path, memmap=True) as hdus:
        events = hdus["EVENTS"].data
        header = hdus["EVENTS"].header
        std_gti = np.column_stack(
            [hdus["STDGTI04"].data["START"], hdus["STDGTI04"].data["STOP"]]
        ).astype(float)

        time = np.asarray(events["TIME"], dtype=float)
        x = np.asarray(events["X"], dtype=float)
        y = np.asarray(events["Y"], dtype=float)
        rawx = np.asarray(events["RAWX"], dtype=float)
        rawy = np.asarray(events["RAWY"], dtype=float)
        pi = np.asarray(events["PI"], dtype=np.int32)
        flag = np.asarray(events["FLAG"], dtype=np.int64)
        pattern = np.asarray(events["PATTERN"], dtype=np.int16)
        ccd = np.asarray(events["CCDNR"], dtype=np.int16)

        source_x, source_y = initial_source_xy(header)
        centroid_base = (
            (flag == cfg_filter["flag"])
            & (pattern <= 4)
            & (pi >= 300)
            & (pi < 10000)
        )
        centroid_radius_units = cfg_filter["centroid_radius_arcsec"] / 0.05
        for _ in range(20):
            near = centroid_base & (
                np.hypot(x - source_x, y - source_y) < centroid_radius_units
            )
            updated = (float(np.mean(x[near])), float(np.mean(y[near])))
            if np.hypot(updated[0] - source_x, updated[1] - source_y) < 1e-8:
                break
            source_x, source_y = updated

        background_x, background_y, source_raw = affine_background_center(
            x, y, rawx, rawy, ccd, (source_x, source_y)
        )
        region_radius_units = cfg_filter["src_radius_arcsec"] / 0.05
        in_source = np.hypot(x - source_x, y - source_y) < region_radius_units
        in_background = (
            np.hypot(x - background_x, y - background_y) < region_radius_units
        )
        in_std_gti = in_intervals(time, std_gti)

        dt = float(cfg_lc["dt_s"])
        first = float(std_gti[0, 0])
        last = float(std_gti[-1, 1])
        n_bins = int(np.ceil((last - first) / dt))
        edges = first + np.arange(n_bins + 1, dtype=float) * dt
        fracexp = interval_fraction(edges, std_gti)

        flare_cfg = cfg_filter["flare"]
        flare_dt = float(flare_cfg["bin_s"])
        n_flare_bins = int(np.ceil((last - first) / flare_dt))
        flare_edges = first + np.arange(n_flare_bins + 1, dtype=float) * flare_dt
        flare_events = (
            (flag == cfg_filter["flag"])
            & (pattern == flare_cfg["pattern"])
            & (pi >= flare_cfg["pi_min"])
            & (pi < flare_cfg["pi_max"])
        )
        flare_counts = np.histogram(time[flare_events], bins=flare_edges)[0]
        quiet = flare_counts / flare_dt < float(flare_cfg["threshold_cps"])
        quiet_intervals = np.column_stack(
            [flare_edges[:-1][quiet], flare_edges[1:][quiet]]
        )
        flare_gti = intersect_intervals(quiet_intervals, std_gti)
        flare_fraction = interval_fraction(edges, flare_gti)

        event_base = (
            (flag == cfg_filter["flag"])
            & (pattern <= cfg_lc["pattern_max"])
            & (ccd == 4)
            & in_std_gti
        )
        counts: dict[str, np.ndarray] = {}
        for name, (lo_kev, hi_kev) in cfg_lc["bands_kev"].items():
            band = (pi >= int(lo_kev * 1000)) & (pi < int(hi_kev * 1000))
            counts[f"{name}_src"] = np.histogram(
                time[event_base & band & in_source], bins=edges
            )[0].astype(float)
            counts[f"{name}_bkg"] = np.histogram(
                time[event_base & band & in_background], bins=edges
            )[0].astype(float)

    window_bins = int(cfg_lag["segment_s"] / dt)
    start, flare_coverage_bins = choose_window(
        np.isclose(fracexp, 1.0, atol=1e-12),
        flare_fraction,
        window_bins,
        int(cfg_lag["max_gap_fill_s"] / dt),
    )
    stop = start + window_bins
    fully_exposed = np.isclose(fracexp[start:stop], 1.0, atol=1e-12)
    segment: dict[str, np.ndarray] = {}
    variance: dict[str, np.ndarray] = {}
    grid = np.arange(window_bins)
    for band in cfg_lc["bands_kev"]:
        net = counts[f"{band}_src"][start:stop] - counts[f"{band}_bkg"][start:stop]
        var = counts[f"{band}_src"][start:stop] + counts[f"{band}_bkg"][start:stop]
        net[~fully_exposed] = np.interp(
            grid[~fully_exposed], grid[fully_exposed], net[fully_exposed]
        )
        var[~fully_exposed] = float(np.mean(var[fully_exposed]))
        segment[band] = net
        variance[band] = var

    diagnostic = {
        "obsid": obsid,
        "expo": expo,
        "source_xy": [source_x, source_y],
        "source_rawxy": list(source_raw),
        "background_xy": [background_x, background_y],
        "window_start_s_from_grid": start * dt,
        "window_start_time": first + start * dt,
        "gap_bins": int(np.count_nonzero(~fully_exposed)),
        "partly_exposed_gap_bins": int(
            np.count_nonzero((fracexp[start:stop] > 0) & ~fully_exposed)
        ),
        "outside_flare_gti_s": float(
            (window_bins - flare_coverage_bins) * dt
        ),
        "counts_whole_exposure": {
            key: int(np.sum(value)) for key, value in counts.items()
        },
    }
    return {
        "soft": segment["soft"],
        "hard": segment["hard"],
        "soft_variance": variance["soft"],
        "hard_variance": variance["hard"],
    }, diagnostic


def derive_lags() -> tuple[list[dict], dict]:
    segments: list[dict[str, np.ndarray]] = []
    diagnostics: list[dict] = []
    for exposure in PARAMS["exposures"]:
        if not exposure["include"]:
            continue
        key = (exposure["obsid"], exposure["expo"])
        if key not in EVENT_FILES:
            continue
        segment, diagnostic = process_exposure(*key)
        segments.append(segment)
        diagnostics.append(diagnostic)

    dt = float(PARAMS["lightcurves"]["dt_s"])
    n = segments[0]["soft"].size
    frequencies = np.fft.rfftfreq(n, dt)[1:-1]
    cross_by_segment = []
    soft_power_by_segment = []
    hard_power_by_segment = []
    for segment in segments:
        soft_fft = np.fft.rfft(segment["soft"] - np.mean(segment["soft"]))[1:-1]
        hard_fft = np.fft.rfft(segment["hard"] - np.mean(segment["hard"]))[1:-1]
        cross_by_segment.append(np.conj(hard_fft) * soft_fft)
        soft_power_by_segment.append(np.abs(soft_fft) ** 2)
        hard_power_by_segment.append(np.abs(hard_fft) ** 2)
    cross = np.mean(cross_by_segment, axis=0)
    soft_power = np.mean(soft_power_by_segment, axis=0)
    hard_power = np.mean(hard_power_by_segment, axis=0)

    soft_noise = float(
        np.mean([np.mean(s["soft_variance"]) * n for s in segments])
    )
    hard_noise = float(
        np.mean([np.mean(s["hard_variance"]) * n for s in segments])
    )

    first_frequency = frequencies[0]
    edges = [first_frequency * (1.0 - 1e-9)]
    factor = float(PARAMS["lags"]["freq_bin_factor"])
    while edges[-1] < frequencies[-1]:
        edges.append(edges[-1] * factor)

    rows: list[dict] = []
    n_segments = len(segments)
    for low, high in zip(edges[:-1], edges[1:]):
        use = (frequencies >= low) & (frequencies < high)
        n_frequency = int(np.count_nonzero(use))
        if n_frequency == 0:
            continue
        k = n_segments * n_frequency
        mean_cross = np.mean(cross[use])
        mean_soft_power = float(np.mean(soft_power[use]))
        mean_hard_power = float(np.mean(hard_power[use]))
        f_mean = float(np.mean(frequencies[use]))
        raw_coherence = float(
            np.abs(mean_cross) ** 2 / (mean_soft_power * mean_hard_power)
        )
        phase = float(np.angle(mean_cross))
        lag = phase / (2 * np.pi * f_mean)
        phase_error = float(
            np.sqrt((1.0 - raw_coherence) / (2.0 * raw_coherence * k))
        )
        lag_error = phase_error / (2 * np.pi * f_mean)
        intrinsic, intrinsic_error = intrinsic_coherence(
            mean_cross,
            mean_soft_power,
            mean_hard_power,
            soft_noise,
            hard_noise,
            k,
            return_uncertainty=True,
            adjust_bias=True,
        )
        intrinsic = float(intrinsic)
        intrinsic_error = float(intrinsic_error)
        reliable = bool(np.isfinite(intrinsic) and k >= 30)
        rows.append(
            {
                "f_low_hz": low,
                "f_high_hz": high,
                "f_mean_hz": f_mean,
                "n_frequency": n_frequency,
                "k": k,
                "lag_s": lag,
                "lag_err_s": lag_error,
                "phase_rad": phase,
                "phase_err_rad": phase_error,
                "raw_coherence": raw_coherence,
                "intrinsic_coherence": intrinsic,
                "intrinsic_coherence_err": intrinsic_error,
                "reliable": int(reliable),
            }
        )

    high_frequency = [
        row
        for row in rows
        if row["reliable"]
        and row["f_mean_hz"] >= 7e-4
        and row["f_mean_hz"] < 5e-3
    ]
    weights = np.array([1.0 / row["lag_err_s"] ** 2 for row in high_frequency])
    lag_values = np.array([row["lag_s"] for row in high_frequency])
    summary = {
        "sign_convention": (
            "lag > 0: hard (1-4 keV) lags soft (0.3-1 keV); "
            "lag < 0: soft lags hard"
        ),
        "libraries": {
            "numpy": np.__version__,
            "astropy": __import__("astropy").__version__,
            "stingray": __import__("stingray").__version__,
            "pyyaml": yaml.__version__,
        },
        "diagnostics": diagnostics,
        "soft_poisson_noise": soft_noise,
        "hard_poisson_noise": hard_noise,
        "frequency_bin_count": len(rows),
        "reliable_bin_indices_zero_based": [
            index for index, row in enumerate(rows) if row["reliable"]
        ],
        "high_frequency_range_hz": [7e-4, 5e-3],
        "high_frequency_reliable_bin_count": len(high_frequency),
        "high_frequency_weighted_mean_lag_s": float(
            np.sum(weights * lag_values) / np.sum(weights)
        ),
        "high_frequency_weighted_mean_error_s": float(
            1.0 / np.sqrt(np.sum(weights))
        ),
    }
    return rows, summary


def main() -> None:
    rows, summary = derive_lags()
    csv_path = HERE / "independent_lag_frequency.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (HERE / "independent_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

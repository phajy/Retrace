#!/usr/bin/env python3
"""Value-by-value phase-2 comparison of the frozen independent R1 output."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read_reference() -> list[dict[str, str]]:
    path = ROOT / "analysis" / "lags" / "lag_frequency.csv"
    with path.open(newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    return list(csv.DictReader(lines))


def main() -> None:
    with (HERE / "independent_lag_frequency.csv").open(newline="") as handle:
        independent = list(csv.DictReader(handle))
    reference = read_reference()
    if len(independent) != len(reference):
        raise RuntimeError(
            f"row-count mismatch: independent={len(independent)}, reference={len(reference)}"
        )

    rows: list[dict] = []
    for index, (own, ref) in enumerate(zip(independent, reference, strict=True)):
        own_lag = float(own["lag_s"])
        ref_lag = float(ref["lag_s"])
        own_error = float(own["lag_err_s"])
        ref_error = float(ref["lag_err_s"])
        own_intrinsic = float(own["intrinsic_coherence"])
        ref_intrinsic = float(ref["coh_intrinsic"])
        rows.append(
            {
                "index_zero_based": index,
                "f_mean_hz_independent": float(own["f_mean_hz"]),
                "f_mean_hz_reference": float(ref["f_mean_hz"]),
                "n_frequency_independent": int(own["n_frequency"]),
                "n_frequency_reference": int(ref["n_freq"]),
                "reliable_independent": int(own["reliable"]),
                "reliable_reference": int(ref["reliable"]),
                "lag_s_independent": own_lag,
                "lag_s_reference": ref_lag,
                "delta_lag_s_independent_minus_reference": own_lag - ref_lag,
                "abs_delta_lag_over_reference_sigma": abs(own_lag - ref_lag)
                / ref_error,
                "lag_err_s_independent": own_error,
                "lag_err_s_reference": ref_error,
                "relative_error_difference": (own_error - ref_error) / ref_error,
                "raw_coherence_independent": float(own["raw_coherence"]),
                "raw_coherence_reference": float(ref["coh_raw"]),
                "intrinsic_coherence_independent": own_intrinsic,
                "intrinsic_coherence_reference": ref_intrinsic,
                "delta_intrinsic_coherence": own_intrinsic - ref_intrinsic,
            }
        )

    with (HERE / "independent_summary.json").open() as handle:
        own_summary = json.load(handle)
    with (ROOT / "analysis" / "lags" / "summary.json").open() as handle:
        ref_summary = json.load(handle)
    own_mean = own_summary["high_frequency_weighted_mean_lag_s"]
    own_mean_error = own_summary["high_frequency_weighted_mean_error_s"]
    ref_high = ref_summary["high_freq_mean_lag"]["7e-4_to_5e-3_Hz"]
    ref_mean = ref_high["weighted_mean_lag_s"]
    ref_mean_error = ref_high["error_s"]

    reliable = [row for row in rows if row["reliable_reference"]]
    result = {
        "phase1_commit": "fb4d748",
        "row_count_independent": len(independent),
        "row_count_reference": len(reference),
        "all_frequency_memberships_identical": all(
            row["n_frequency_independent"] == row["n_frequency_reference"]
            for row in rows
        ),
        "all_reliability_flags_identical": all(
            row["reliable_independent"] == row["reliable_reference"] for row in rows
        ),
        "reliable_bin_count": len(reliable),
        "max_reliable_abs_delta_lag_s": max(
            abs(row["delta_lag_s_independent_minus_reference"]) for row in reliable
        ),
        "max_reliable_abs_delta_lag_over_reference_sigma": max(
            row["abs_delta_lag_over_reference_sigma"] for row in reliable
        ),
        "max_reliable_abs_relative_error_difference": max(
            abs(row["relative_error_difference"]) for row in reliable
        ),
        "max_reliable_abs_delta_intrinsic_coherence": max(
            abs(row["delta_intrinsic_coherence"]) for row in reliable
        ),
        "high_frequency_mean": {
            "independent_lag_s": own_mean,
            "reference_lag_s": ref_mean,
            "delta_lag_s_independent_minus_reference": own_mean - ref_mean,
            "abs_delta_over_reference_sigma": abs(own_mean - ref_mean)
            / ref_mean_error,
            "independent_error_s": own_mean_error,
            "reference_error_s": ref_mean_error,
            "relative_error_difference": (own_mean_error - ref_mean_error)
            / ref_mean_error,
            "independent_n_bins": own_summary[
                "high_frequency_reliable_bin_count"
            ],
            "reference_n_bins": ref_high["n_bins"],
        },
        "criterion": {
            "frequency_memberships_and_reliability_identical": True,
            "max_reliable_abs_delta_over_sigma": 0.10,
            "max_reliable_abs_relative_error_difference": 0.01,
            "max_scalar_abs_delta_over_sigma": 0.10,
        },
    }
    result["r1_matches_frozen_criterion"] = bool(
        result["all_frequency_memberships_identical"]
        and result["all_reliability_flags_identical"]
        and result["max_reliable_abs_delta_lag_over_reference_sigma"] <= 0.10
        and result["max_reliable_abs_relative_error_difference"] <= 0.01
        and result["high_frequency_mean"]["abs_delta_over_reference_sigma"] <= 0.10
    )

    with (HERE / "phase2_bin_comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (HERE / "phase2_comparison.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

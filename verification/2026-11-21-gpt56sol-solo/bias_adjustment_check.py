#!/usr/bin/env python3
"""Show the effect of enabling Stingray's Ingram-2019 bias iteration.

This is a labelled phase-2 diagnostic in the verifier folder. It reconstructs
the binned cross spectrum from the rounded committed CSV values and does not
modify explainer files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from stingray.fourier import intrinsic_coherence


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main() -> None:
    with (ROOT / "analysis/lags/lag_frequency.csv").open() as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    comparisons = []
    for index, row in enumerate(rows):
        soft_power = float(row["power_soft"])
        hard_power = float(row["power_hard"])
        magnitude = np.sqrt(
            float(row["coh_raw"]) * soft_power * hard_power
        )
        cross = magnitude * np.exp(1j * float(row["phase_rad"]))
        args = (
            cross,
            soft_power,
            hard_power,
            float(row["noise_soft"]),
            float(row["noise_hard"]),
            int(row["K"]),
        )
        without_iteration = float(intrinsic_coherence(*args, adjust_bias=False))
        with_iteration = float(intrinsic_coherence(*args, adjust_bias=True))
        comparisons.append(
            {
                "index_zero_based": index,
                "f_mean_hz": float(row["f_mean_hz"]),
                "reliable": int(row["reliable"]),
                "committed_intrinsic_coherence": float(row["coh_intrinsic"]),
                "stingray_adjust_bias_false": without_iteration,
                "stingray_adjust_bias_true": with_iteration,
                "true_minus_false": with_iteration - without_iteration,
            }
        )
    reliable = [row for row in comparisons if row["reliable"]]
    output = {
        "note": (
            "Calculated from six-significant-digit committed CSV values, so "
            "small reconstruction rounding is expected."
        ),
        "max_reliable_abs_true_minus_false": max(
            abs(row["true_minus_false"]) for row in reliable
        ),
        "max_reliable_abs_false_minus_committed": max(
            abs(
                row["stingray_adjust_bias_false"]
                - row["committed_intrinsic_coherence"]
            )
            for row in reliable
        ),
        "rows": comparisons,
    }
    (HERE / "bias_adjustment_effect.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {key: value for key, value in output.items() if key != "rows"},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

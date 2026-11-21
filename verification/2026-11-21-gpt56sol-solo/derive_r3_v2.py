#!/usr/bin/env python3
"""Post-comparison extraction of R3 using the frozen phase-1 flare rule.

R3's identity was not available in the permitted phase-1 record.  This script
duplicates only the flare-GTI part already present in phase-1 derive.py and
records the total that phase 1 failed to emit.  It was written after unblinding,
so it is explicitly secondary and does not retroactively alter phase 1.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml
from astropy.io import fits


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PARAMS = yaml.safe_load((ROOT / "params.yaml").read_text())
EVENT_FILES = {
    ("0511580101", "PNS001"): "P0511580101PNS001PIEVLI0000.FTZ",
    ("0511580201", "PNS001"): "P0511580201PNS001PIEVLI0000.FTZ",
    ("0511580301", "PNU002"): "P0511580301PNU002PIEVLI0000.FTZ",
    ("0511580401", "PNU002"): "P0511580401PNU002PIEVLI0000.FTZ",
}


def interval_total(intersections_left: np.ndarray, right: np.ndarray) -> float:
    total = 0.0
    for left_start, left_stop in intersections_left:
        for right_start, right_stop in right:
            total += max(
                0.0,
                min(left_stop, right_stop) - max(left_start, right_start),
            )
    return total


def main() -> None:
    flare = PARAMS["filter"]["flare"]
    rows = []
    for exposure in PARAMS["exposures"]:
        if not exposure["include"]:
            continue
        key = (exposure["obsid"], exposure["expo"])
        path = (
            ROOT
            / "reduction"
            / "raw"
            / exposure["obsid"]
            / EVENT_FILES[key]
        )
        with fits.open(path, memmap=True) as hdus:
            events = hdus["EVENTS"].data
            standard = np.column_stack(
                [
                    hdus["STDGTI04"].data["START"],
                    hdus["STDGTI04"].data["STOP"],
                ]
            ).astype(float)
            times = np.asarray(events["TIME"], dtype=float)
            selected = (
                (np.asarray(events["FLAG"], dtype=np.int64) == 0)
                & (np.asarray(events["PATTERN"], dtype=np.int16) == flare["pattern"])
                & (np.asarray(events["PI"], dtype=np.int32) >= flare["pi_min"])
                & (np.asarray(events["PI"], dtype=np.int32) < flare["pi_max"])
            )
        first, last = float(standard[0, 0]), float(standard[-1, 1])
        width = float(flare["bin_s"])
        count = int(np.ceil((last - first) / width))
        edges = first + np.arange(count + 1) * width
        counts = np.histogram(times[selected], bins=edges)[0]
        quiet = counts / width < float(flare["threshold_cps"])
        quiet_intervals = np.column_stack(
            [edges[:-1][quiet], edges[1:][quiet]]
        )
        total = interval_total(quiet_intervals, standard)
        rows.append(
            {
                "exposure": f"{key[0]}_{key[1]}",
                "flare_filtered_gti_s": total,
            }
        )
    output = {
        "status": "post-comparison extraction; secondary to frozen phase 1",
        "rule": (
            "phase-1 rule: 100 s bins anchored at first STDGTI04 start; "
            "FLAG=0, PATTERN=0, PI in [10000,12000), counts/100 < 0.4; "
            "quiet bins intersected with STDGTI04"
        ),
        "exposures": rows,
        "total_ks": sum(row["flare_filtered_gti_s"] for row in rows) / 1000.0,
    }
    (HERE / "phase2_r3_summary.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

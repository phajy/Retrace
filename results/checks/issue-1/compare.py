#!/usr/bin/env python3
"""Check request #1: compare the baseline lags with the no-background-subtraction run.

Applies the criteria in PLAN.md (fixed before the run) mechanically and writes
comparison.json and comparison.png next to this script.

Baseline: analysis/lags/{summary.json,lag_frequency.csv} at commit 9eea9a1 (read with `git show`).
Test:     test_summary.json and test_lag_frequency.csv in this folder, copied from the DVC experiment
          `issue-1-no-bkg-subtraction` (`dvc exp run --temp -S lags.background_subtract=false` on 9eea9a1).

Usage (from the repository root):  python results/checks/issue-1/compare.py
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
BASE_COMMIT = "9eea9a1"
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#1f1f1e", "#8a8986"


def git_show(path: str) -> str:
    return subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{path}"], text=True)


def read_csv(text: str) -> list[dict]:
    rows = csv.DictReader(io.StringIO("".join(l for l in text.splitlines(True) if not l.startswith("#"))))
    return [{k: float(v) for k, v in r.items()} for r in rows]


def crossing_pairs(rows: list[dict]) -> list[tuple[float, float]]:
    """Consecutive reliable bins where the lag goes from positive to negative (f_mean of each)."""
    rel = [r for r in rows if r["reliable"] == 1]
    return [(a["f_mean_hz"], b["f_mean_hz"]) for a, b in zip(rel, rel[1:]) if a["lag_s"] > 0 >= b["lag_s"]]


def main():
    base_s, base_r = json.loads(git_show("analysis/lags/summary.json")), read_csv(git_show("analysis/lags/lag_frequency.csv"))
    test_s = json.load(open(HERE / "test_summary.json"))
    test_r = read_csv(open(HERE / "test_lag_frequency.csv").read())
    assert base_s["background_subtract"] is True and test_s["background_subtract"] is False
    assert [r["f_mean_hz"] for r in base_r] == [r["f_mean_hz"] for r in test_r], "frequency grids differ"

    out, flags = {"baseline_commit": BASE_COMMIT, "items": {}}, []

    # items 1 and 2: weighted mean lags (threshold: baseline 1 sigma)
    for key, grp, rng in [("1_high_freq_mean", "high_freq_mean_lag", "7e-4_to_5e-3_Hz"),
                          ("2_low_freq_mean", "low_freq_mean_lag", "1e-4_to_5e-4_Hz")]:
        b, t = base_s[grp][rng], test_s[grp][rng]
        d = t["weighted_mean_lag_s"] - b["weighted_mean_lag_s"]
        sig = abs(d) > b["error_s"]
        out["items"][key] = {"range_hz": rng, "baseline": [b["weighted_mean_lag_s"], b["error_s"], b["n_bins"]],
                             "test": [t["weighted_mean_lag_s"], t["error_s"], t["n_bins"]],
                             "difference_s": d, "difference_in_baseline_sigma": d / b["error_s"], "significant": sig}
        flags += [key] if sig else []

    # item 3: sign change (threshold: a different pair of bins)
    pb, pt = crossing_pairs(base_r), crossing_pairs(test_r)
    sig = pb != pt
    out["items"]["3_sign_change"] = {"baseline_hz": base_s["positive_to_negative_crossing_hz"],
                                     "test_hz": test_s["positive_to_negative_crossing_hz"],
                                     "baseline_bin_pairs": pb, "test_bin_pairs": pt, "significant": sig}
    flags += ["3_sign_change"] if sig else []

    # item 4: most negative reliable bin (reported; covered by item 5's per-bin threshold)
    out["items"]["4_most_negative_bin"] = {"baseline": base_s["most_negative_reliable_bin"],
                                           "test": test_s["most_negative_reliable_bin"]}

    # item 5: every bin; threshold applies to bins reliable in both runs
    per_bin = []
    for b, t in zip(base_r, test_r):
        both = b["reliable"] == 1 and t["reliable"] == 1
        z = (t["lag_s"] - b["lag_s"]) / b["lag_err_s"]
        per_bin.append({"f_mean_hz": b["f_mean_hz"], "baseline_lag_s": b["lag_s"], "baseline_err_s": b["lag_err_s"],
                        "test_lag_s": t["lag_s"], "test_err_s": t["lag_err_s"],
                        "baseline_reliable": int(b["reliable"]), "test_reliable": int(t["reliable"]),
                        "difference_in_baseline_sigma": z, "significant": bool(both and abs(z) > 1)})
    out["items"]["5_per_bin"] = per_bin
    flags += [f"5_bin_{p['f_mean_hz']:.3g}Hz" for p in per_bin if p["significant"]]
    out["reliability_changed_hz"] = [p["f_mean_hz"] for p in per_bin if p["baseline_reliable"] != p["test_reliable"]]
    out["significant_change"] = bool(flags)
    out["triggered"] = flags
    json.dump(out, open(HERE / "comparison.json", "w"), indent=2)

    # figure: lags of both runs (top), per-bin difference in baseline sigma (bottom)
    f = np.array([p["f_mean_hz"] for p in per_bin])
    both = np.array([p["baseline_reliable"] and p["test_reliable"] for p in per_bin], bool)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7.5), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    for key, color, marker, shift, label in [("baseline", BLUE, "o", 1 / 1.04, "baseline: background subtracted"),
                                             ("test", ORANGE, "s", 1.04, "test: no background subtraction")]:
        lag = np.array([p[f"{key}_lag_s"] for p in per_bin])
        err = np.array([p[f"{key}_err_s"] for p in per_bin])
        rel = np.array([p[f"{key}_reliable"] for p in per_bin], bool)
        a1.errorbar(f[rel] * shift, lag[rel], err[rel], fmt=marker, ms=6, color=color, lw=1.2, capsize=0, label=label)
        a1.errorbar(f[~rel] * shift, lag[~rel], err[~rel], fmt=marker, ms=6, mfc="none", color=color, lw=0.8,
                    alpha=0.45, capsize=0)
    a1.axhline(0, color=MUTED, lw=0.8)
    a1.set_ylim(-100, 300)
    a1.set_ylabel("lag (s)   [> 0: hard lags soft]", color=INK)
    a1.set_title("Check request #1: lags with and without background subtraction (open symbols: not reliable)",
                 fontsize=10, color=INK)
    a1.legend(loc="upper right", fontsize=9, frameon=False)
    z = np.array([p["difference_in_baseline_sigma"] for p in per_bin])
    a2.axhspan(-1, 1, color="#eeeeec", lw=0)
    a2.axhline(0, color=MUTED, lw=0.8)
    a2.plot(f[both], z[both], "o", ms=6, color=INK, label="bins reliable in both runs")
    a2.plot(f[~both], np.clip(z[~both], -3, 3), "o", ms=6, mfc="none", color=MUTED, label="other bins (clipped at ±3)")
    a2.set_ylim(-3.2, 3.2)
    a2.set_ylabel("(test − baseline) / σ_baseline", color=INK)
    a2.set_xlabel("frequency (Hz)", color=INK)
    a2.set_xscale("log")
    a2.legend(loc="lower left", fontsize=8, frameon=False)
    a2.text(0.99, 0.92, "grey band: ±1σ (threshold in PLAN.md)", transform=a2.transAxes, ha="right", va="top",
            fontsize=8, color=MUTED)
    for ax in (a1, a2):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "comparison.png", dpi=110)

    # console summary
    for key in ("1_high_freq_mean", "2_low_freq_mean"):
        it = out["items"][key]
        print(f"{key}: baseline {it['baseline'][0]:+.1f} ± {it['baseline'][1]:.1f} s, test {it['test'][0]:+.1f} ± "
              f"{it['test'][1]:.1f} s, diff {it['difference_s']:+.2f} s = {it['difference_in_baseline_sigma']:+.2f} sigma")
    it = out["items"]["3_sign_change"]
    print(f"3_sign_change: baseline {it['baseline_hz']}, test {it['test_hz']}, same bin pair: {not it['significant']}")
    it = out["items"]["4_most_negative_bin"]
    print(f"4_most_negative_bin: baseline {it['baseline']}, test {it['test']}")
    print("5_per_bin (reliable in both):")
    for p in per_bin:
        if p["baseline_reliable"] and p["test_reliable"]:
            print(f"   {p['f_mean_hz']:.3g} Hz: {p['baseline_lag_s']:+7.1f} ± {p['baseline_err_s']:5.1f}  ->  "
                  f"{p['test_lag_s']:+7.1f} ± {p['test_err_s']:5.1f}   ({p['difference_in_baseline_sigma']:+.2f} sigma)")
    print("reliability changed at:", out["reliability_changed_hz"])
    print("SIGNIFICANT CHANGE:", out["significant_change"], out["triggered"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read Fig. 3 of Fabian et al. 2009 from the arXiv PDF's drawing commands.

The PDF is not stored in this repository. Pass its path on the command line.
This script only reports coordinates. It does not compare them with anything.

Requires PyMuPDF. It was run with PyMuPDF 1.28.2.

Page coordinates below are PDF user-space points after the content stream's
transformation matrix: origin at the bottom-left of the page, y upward,
1 unit = 1/72 inch. PyMuPDF returns y downward, so y_up = 792 - y_down.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys

import pymupdf


PAGE_INDEX = 8  # PDF page 9, 0-based
PAGE_HEIGHT = 792.0


def line_ends(drawing):
    item = drawing["items"][0]
    if item[0] != "l" or len(drawing["items"]) != 1:
        return None
    return item[1], item[2]


def circle_center(drawing):
    pts = [item[-1] for item in drawing["items"] if item[0] == "c"]
    if len(pts) != 4:
        raise ValueError(f"expected 4 curve ends, got {len(pts)}")
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--csv", help="write points.csv to this path")
    args = parser.parse_args()

    doc = pymupdf.open(args.pdf)
    page = doc[PAGE_INDEX]
    if abs(page.rect.width - 612) > 1e-6 or abs(page.rect.height - PAGE_HEIGHT) > 1e-6:
        sys.exit(f"unexpected page size {page.rect}")

    drawings = page.get_drawings()
    circles = []
    thin_h = []
    thin_v = []
    thick = []
    for drawing in drawings:
        kinds = "".join(it[0] for it in drawing["items"])
        if kinds == "cccc" and drawing.get("fill") == (0.0, 0.0, 0.0):
            circles.append(circle_center(drawing))
            continue
        ends = line_ends(drawing) if kinds == "l" else None
        if ends is None:
            continue
        p1, p2 = ends
        width = drawing.get("width") or 0
        rec = (p1.x, p1.y, p2.x, p2.y, width)
        if width < 0.3:
            if abs(p1.y - p2.y) < 1e-3 and abs(p1.x - p2.x) > 1:
                thin_h.append((min(p1.x, p2.x), max(p1.x, p2.x), (p1.y + p2.y) / 2))
            elif abs(p1.x - p2.x) < 1e-3 and abs(p1.y - p2.y) > 1:
                thin_v.append(((p1.x + p2.x) / 2, min(p1.y, p2.y), max(p1.y, p2.y)))
        else:
            thick.append(rec)

    # Axis box: the four long sides. Bottom has the largest y_down.
    horiz = [r for r in thick if abs(r[1] - r[3]) < 1e-3 and abs(r[0] - r[2]) > 100]
    vert = [r for r in thick if abs(r[0] - r[2]) < 1e-3 and abs(r[1] - r[3]) > 100]
    if len(horiz) < 2 or len(vert) < 2:
        sys.exit(f"could not find the axis box ({len(horiz)} horiz, {len(vert)} vert)")
    y_bottom = max((r[1] + r[3]) / 2 for r in horiz)
    y_top = min((r[1] + r[3]) / 2 for r in horiz)
    x_left = min((r[0] + r[2]) / 2 for r in vert)
    x_right = max((r[0] + r[2]) / 2 for r in vert)

    # Major ticks are the longer strokes on the bottom and left spines.
    def is_major(length):
        return length > 3

    bottom_majors = sorted(
        (r[0] + r[2]) / 2
        for r in thick
        if abs(r[0] - r[2]) < 1e-3
        and abs(((r[1] + r[3]) / 2) - y_bottom) < 3
        and is_major(abs(r[1] - r[3]))
    )
    left_majors = sorted(
        (r[1] + r[3]) / 2
        for r in thick
        if abs(r[1] - r[3]) < 1e-3
        and abs(((r[0] + r[2]) / 2) - x_left) < 3
        and is_major(abs(r[0] - r[2]))
    )
    # The corner ticks sit on both a spine and a corner. Keep x positions that
    # fall on the bottom spine, including the left corner, and y positions on
    # the left spine, including both corners.
    if len(bottom_majors) != 4:
        sys.exit(f"expected 4 major frequency ticks, found {bottom_majors}")
    if len(left_majors) != 6:
        sys.exit(f"expected 6 major lag ticks, found {left_majors}")

    # Labels, read from the page so the tick assignment is not typed in by hand.
    # Frequency labels use a unicode minus: 10−5, 10−4, 10−3, and 0.01.
    words = page.get_text("words")
    freq_labels = []
    lag_labels = []
    for x0, y0, x1, y1, text, *_ in words:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # Axis labels sit just outside the box. The caption repeats "10−4"
        # further down the page and must not be used as a tick.
        if text in {"10−5", "10−4", "10−3"} and cy < 490:
            freq_labels.append((float(text.replace("−", "-")[2:]), cx, cy))
        elif text == "0.01" and cy < 490:
            freq_labels.append((math.log10(0.01), cx, cy))
        elif text in {"200", "150", "100", "50", "0", "−50"} and cx < 175 and cy < 470:
            lag_labels.append((float(text.replace("−", "-")), cx, cy))
    freq_labels.sort()
    if [round(v, 5) for v, _, _ in freq_labels] != [-5, -4, -3, -2]:
        sys.exit(f"unexpected frequency labels {freq_labels}")
    label_values = [1e-5, 1e-4, 1e-3, 1e-2]
    # Pair each label with the nearest major bottom tick.
    used = set()
    x_ticks = {}
    for value, (_, cx, _) in zip(label_values, freq_labels):
        j = min(
            (i for i in range(len(bottom_majors)) if i not in used),
            key=lambda i: abs(bottom_majors[i] - cx),
        )
        used.add(j)
        x_ticks[value] = bottom_majors[j]
    lag_labels_sorted = sorted(lag_labels, key=lambda t: -t[0])
    if [v for v, _, _ in lag_labels_sorted] != [200, 150, 100, 50, 0, -50]:
        sys.exit(f"unexpected lag labels {lag_labels}")
    used = set()
    y_ticks = {}
    for value, _, cy in lag_labels_sorted:
        j = min(
            (i for i in range(len(left_majors)) if i not in used),
            key=lambda i: abs(left_majors[i] - cy),
        )
        used.add(j)
        y_ticks[value] = left_majors[j]

    x0, x1 = x_ticks[1e-5], x_ticks[1e-2]
    log0, log1 = -5.0, -2.0

    def f_of_x(x):
        return 10 ** (log0 + (x - x0) / (x1 - x0) * (log1 - log0))

    y0_down, y1_down = y_ticks[-50], y_ticks[200]

    def lag_of_ydown(y_down):
        return -50 + (y0_down - y_down) / (y0_down - y1_down) * 250

    print(f"pymupdf {pymupdf.version[0]}")
    print(f"n_circles {len(circles)}")
    print(f"n_horizontal {len(thin_h)}")
    print(f"n_vertical {len(thin_v)}")
    print("x_ticks_pt")
    for value in label_values:
        print(f"  {value:.0e} {x_ticks[value]:.16g}")
    print("x_tick_residuals_dex")
    for value in label_values:
        print(f"  {value:.0e} {math.log10(f_of_x(x_ticks[value])) - math.log10(value):+.3e}")
    print("y_ticks_down_pt")
    for value in (200, 150, 100, 50, 0, -50):
        print(f"  {value:g} {y_ticks[value]:.16g}")
    print("y_tick_residuals_s")
    for value in (200, 150, 100, 50, 0, -50):
        print(f"  {value:g} {lag_of_ydown(y_ticks[value]) - value:+.3e}")
    print(f"axis_x_pt {x_left:.16g} {x_right:.16g}")
    print(f"axis_f_hz {f_of_x(x_left):.16g} {f_of_x(x_right):.16g}")
    print(f"axis_y_down_pt {y_top:.16g} {y_bottom:.16g}")
    print(f"calibration_y_up_pt {PAGE_HEIGHT - y0_down:.16g} {PAGE_HEIGHT - y1_down:.16g}")
    print(f"top_edge_is_200 {abs(y_top - y_ticks[200]) < 1e-6}")
    print(f"bottom_edge_is_m50 {abs(y_bottom - y_ticks[-50]) < 1e-6}")
    print(f"left_edge_is_1em5 {abs(x_left - x_ticks[1e-5]) < 1e-6}")

    if len(circles) != 12 or len(thin_h) != 12 or len(thin_v) != 12:
        sys.exit("unexpected number of markers or bars")

    circles = sorted(circles, key=lambda c: c[0])
    rows = []
    print("POINTS")
    for i, (cx, cy) in enumerate(circles, start=1):
        h = min(thin_h, key=lambda seg: abs(seg[2] - cy) + abs((seg[0] + seg[1]) / 2 - cx))
        v = min(thin_v, key=lambda seg: abs(seg[0] - cx))
        top_on_edge = abs(v[1] - y_top) < 0.02
        mid_left_pt = cx - (h[0] + h[1]) / 2
        bits = []
        if top_on_edge:
            bits.append("upper end of the vertical line lies on the top edge of the plot")
        if i == 1:
            bits.append("horizontal segment starts inside the plot and abuts the next segment")
        elif i == len(circles):
            bits.append("horizontal segment abuts the previous segment and stops short of the right edge")
        else:
            bits.append("horizontal segment abuts the neighbouring segments")
        bits.append(f"segment midpoint is {mid_left_pt:.3f} pt left of the marker")
        rows.append(
            {
                "point": i,
                "series": "main",
                "f_hz": f"{f_of_x(cx):.16g}",
                "lag_s": f"{lag_of_ydown(cy):.16g}",
                "lag_top_s": f"{lag_of_ydown(v[1]):.16g}",
                "lag_bottom_s": f"{lag_of_ydown(v[2]):.16g}",
                "f_left_hz": f"{f_of_x(h[0]):.16g}",
                "f_right_hz": f"{f_of_x(h[1]):.16g}",
                "marker": "filled circle",
                "note": "; ".join(bits),
            }
        )
        print(
            "\t".join(
                [
                    str(i),
                    f"{cx:.16g}",
                    f"{cy:.16g}",
                    f"{f_of_x(cx):.16g}",
                    f"{lag_of_ydown(cy):.16g}",
                    f"{f_of_x(h[0]):.16g}",
                    f"{f_of_x(h[1]):.16g}",
                    f"{lag_of_ydown(v[1]):.16g}",
                    f"{lag_of_ydown(v[2]):.16g}",
                    f"{v[0] - cx:+.6e}",
                    f"{h[2] - cy:+.6e}",
                    f"{(h[0] + h[1]) / 2 - cx:+.6e}",
                    f"{(v[1] + v[2]) / 2 - cy:+.6e}",
                    "top_on_edge" if top_on_edge else "top_inside",
                    f"{h[0]:.16g}",
                    f"{h[1]:.16g}",
                    f"{v[1]:.16g}",
                    f"{v[2]:.16g}",
                ]
            )
        )

    if args.csv:
        fields = [
            "point",
            "series",
            "f_hz",
            "lag_s",
            "lag_top_s",
            "lag_bottom_s",
            "f_left_hz",
            "f_right_hz",
            "marker",
            "note",
        ]
        with open(args.csv, "w", newline="\n") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()

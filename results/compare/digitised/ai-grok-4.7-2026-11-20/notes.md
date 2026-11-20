# Digitisation of Fabian et al. 2009, Fig. 3

Grok 4.7 High Fast, in Cursor. Started 2026-11-20T10:04Z, finished 2026-11-20T10:10Z.
Nothing here was compared with the Retrace lag spectrum. The points are only what is drawn.

## Prompt

The message I was given, word for word:

> Please now follow the instructions in @results/compare/DIGITISE.md

That is not the template prompt printed at the bottom of `DIGITISE.md`. The template's `<COMMIT>` and `<ID>` placeholders were not filled in, and I was not started in a new empty folder. The checkout was already this clone, on `main` at `13438ec8d0b3b7976e3613425aee3e8f6a03045a`. I made the branch `digitise/ai-grok-4.7-2026-11-20` from that commit. I did not look at any other commit.

## Files opened

In this repository, during this task:

* `results/compare/DIGITISE.md`
* `results/compare/PLAN.md`
* `results/compare/digitised/ai-grok-4.7-2026-11-20/extract_fig3.py` (written here)
* `results/compare/digitised/ai-grok-4.7-2026-11-20/points.csv` (written by that script)
* `results/compare/digitised/ai-grok-4.7-2026-11-20/digitisation.json` and this file

`PLAN.md` describes how a later comparison will use digitised frequencies. It does not contain Fig. 3's coordinates. I did not use its frequency windows to place any point.

I did not open `README.md`, `docs/`, `analysis/`, `verification/`, or any other file under `results/`. I did not open another digitiser's folder. `had_seen_other_digitisation` is false.

`had_seen_retrace_result` is true. On 2026-11-19, in an earlier session in this same workspace, I re-ran the pipeline and read the R1 page, `analysis/lags/summary.json`, and `analysis/lags/lag_frequency.csv`. I did not open those files again for this reading, and I did not move any coordinate toward those numbers. The values in `points.csv` come from the PDF paths and the axis ticks.

## URLs fetched

* `https://arxiv.org/pdf/0905.4383.pdf`
* `https://arxiv.org/pdf/0905.4383v1.pdf` (same bytes as the URL above)
* `https://export.arxiv.org/api/query?id_list=0905.4383`

The API record is `0905.4383v1` and lists no later version. SHA-256 of the PDF is `e8846b5df83b809ec11ea7b425ef1a7ae555668372da34a6d353b8a3d52b5388`. `pdfinfo` says the file was produced on 23 October 2018 by dvips and Ghostscript, from LaTeX. I did not have the *Nature* PDF, so that version was not checked. The PDF was kept outside the repository and is not committed.

## What I did

1. Confirmed the PDF has no embedded images (`pdfimages -list` prints no rows). Fig. 3 is vector graphics.
2. Found the figure on page 9 by extracting the page text. The printed page number is also 9. The page is 612 by 792 pt.
3. Read the drawing commands with PyMuPDF 1.28.2, installed in a temporary virtual environment, not the project's `.venv`. The script is `extract_fig3.py`.
4. Separated the strokes by width. The axis box, ticks, and the zero line are about 0.484 pt wide. The lines through the data are about 0.161 pt wide. The markers are filled black circles made of four Bézier curves, with no stroke.
5. Took each marker's centre from the on-curve ends of those curves (the left, right, top, and bottom of the circle).
6. Paired each marker with the thin vertical line at its x and the thin horizontal line at its y.
7. Calibrated frequency from the two major bottom ticks furthest apart, matched to the labels `10−5` and `0.01` by nearest label. The scale is logarithmic. Calibrated lag from the major left ticks labelled −50 and 200. The scale is linear. PDF y from PyMuPDF increases downward; the `pixel` values in `digitisation.json` are page points with the origin at the bottom-left and y upward (`y_up = 792 - y_down`). `render_dpi` is null.

The content stream applies `0.1 0 0 0.1 0 0 cm` and then, around each path, `1.00562 0 0 0.994384 0 0 cm`. A stream coordinate `(xs, ys)` is at page point `x = 0.1 * 1.00562 * xs`, `y_up = 0.1 * 0.994384 * ys`. The script uses the page points, after that transform.

There are 12 filled circles and 12 of each thin line. No open symbols, arrows, or points outside the box.

## Axis check

Major frequency ticks, and the residual of a log line fixed by the outer two:

| Label | x (pt, y down) | Residual |
|---|---:|---:|
| 10⁻⁵ | 172.6156768798828 | 0 (used) |
| 10⁻⁴ | 266.8352355957031 | −1.102×10⁻⁴ dex |
| 10⁻³ | 361.0859375 | +1.101×10⁻⁴ dex |
| 0.01 | 455.3055114746094 | 0 (used) |

Major lag ticks, and the residual of a straight line fixed by −50 and 200:

| Label (s) | y (pt, y down) | Residual (s) |
|---:|---:|---:|
| 200 | 256.0558471679688 | 0 (used) |
| 150 | 295.8381652832031 | −0.0087 |
| 100 | 335.6195068359375 | −0.016 |
| 50 | 375.3690185546875 | +0.016 |
| 0 | 415.1513366699219 | +0.0075 |
| −50 | 454.9326782226562 | 0 (used) |

The left spine is the 10⁻⁵ tick. The top spine is the 200 s tick. The bottom spine is the −50 s tick. The right spine is not a labelled tick. Its frequency, on the same log line, is 0.01200013371058352 Hz. That is `plotted_range` for x. Lag `plotted_range` is −50 to 200.

Eight minor ticks sit between each pair of major frequency ticks, at the positions expected for 2, 3, …, 9 times the decade. I did not use them in the calibration.

## What the marks are

Every marker is a filled circle. There is one series (`main`).

The thin vertical line passes through the marker. Its x is within 0.0025 pt of the circle centre (about 2×10⁻⁵ dex). Apart from point 2, the marker is within 0.016 pt of the line's midpoint, about 0.02 s. The lines have no end caps. The figure caption does not say what these lines are, so `error_bars_stated_as` is `not stated`. I recorded the y of each drawn end as `lag_top_s` and `lag_bottom_s`.

Point 2's upper end is the same coordinate as the top of the axis, the 200 s tick. The line is not drawn past the frame. I recorded 200 because that is the end that is drawn, and said so in `note`. I do not know whether a longer bar was clipped.

Each marker also has a thin horizontal segment at its lag. Neighbouring segments share endpoints, so together they tile a frequency interval without gaps or overlaps. They are not centred on the markers. The midpoint is left of the circle by 12.036 pt on point 1 and by 0.57–1.93 pt on the others. The first segment starts at x = 209.959 pt, inside the plot, not on the left spine. The last ends at x = 461.664 pt, 1.103 pt short of the right spine (462.767 pt). I put those ends in `f_left_hz` and `f_right_hz` because they are the horizontal extents drawn through the points. I am not sure they are symmetric errors rather than bin edges. The columns would have been empty only if the ends were not there.

The only other line inside the box is the full-width line at 0 s, drawn in the heavier axis stroke.

## What I could not do

* I could not check the *Nature* printing.
* I could not see any continuation of point 2's upper bar beyond the top of the plot.
* I could not tell, from the figure or its caption, what the vertical lines are defined to be.
* I was not blind to the project's own lag spectrum, for the reason above.

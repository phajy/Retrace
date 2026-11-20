# Digitising Fig. 3 of Fabian et al. 2009: instructions for digitisers

These instructions are for the people and agents who read the data points off Fig. 3 of Fabian et al. 2009
(F09; *Nature* 459, 540; arXiv:0905.4383). The plan for the comparison, with its criteria fixed in advance,
is in [`PLAN.md`](PLAN.md). Your only job is to record the points as accurately as you can, and to say exactly
how you did it. You do not compare anything.

## Rules
* **Source.** Use the arXiv version: <https://arxiv.org/abs/0905.4383>. Download the PDF of the latest version
  and record the version number and the file's SHA-256 (`shasum -a 256 <file>`). Optionally, and only if you have
  access, say whether Fig. 3 in the *Nature* version looks the same.
* **Copyright.** Do not commit the PDF, the figure, a crop or screenshot of it, or any file that contains the image
  (WebPlotDigitizer's `.tar` project does). Do not copy the caption or other paper text; paraphrase. Short axis
  labels may be quoted.
* **Method.** Your choice. For example, WebPlotDigitizer on the page rendered at 600 dpi or more, or reading the
  coordinates from the PDF's own drawing commands if the figure is stored as vector graphics. Describe what you did
  well enough for someone else to repeat it. Commit any script you wrote.
* **Record what is there, nothing more.** Every data point in the figure, including ones drawn differently
  (open symbols, arrows, points at the edge of the plot). Don't round, smooth or drop anything, and don't
  guess values you cannot see: leave them empty and say why in the `note` column.
* **Independence.** Do not look at the other digitiser's values before yours are saved and committed. AI digitisers:
  do not open any file in the repository apart from this one and `PLAN.md`, and do not look at other branches or
  commits. The project's own result must not influence your reading.
* **No recollections.** Read the figure as published. If you know anything about how it was made from outside the
  paper (for example as an author), don't use it here. Write it in your notes as a separate item.

## What to write
One folder per digitiser: `results/compare/digitised/<id>/`, where `<id>` is `ay` for Andy Young, or
`ai-<model>-<YYYY-MM-DD>` for an AI agent (for example `ai-grok-4.7-2026-11-20`). It contains three files.

### `points.csv`
Plain CSV with a header row, `\n` line endings, and no comment lines. One row per data point, in order of
increasing frequency. Values are in the plotted units: frequency in Hz and lag in seconds.

| Column | Meaning |
|---|---|
| `point` | 1, 2, 3, … in order of increasing frequency |
| `series` | `main` if the figure has one data series. Otherwise a short label per series or panel |
| `f_hz` | frequency at the centre of the marker |
| `lag_s` | lag at the centre of the marker, with the sign as plotted |
| `lag_top_s`, `lag_bottom_s` | lag values at the top and bottom ends of the vertical error bar (the ends themselves, not their distance from the point). Empty if not visible |
| `f_left_hz`, `f_right_hz` | frequencies at the left and right ends of a horizontal error bar. Empty if there is none |
| `marker` | short description, e.g. `filled circle` |
| `note` | anything unusual, e.g. `bar hidden behind marker`, `arrow`, `at edge of plot` |

### `digitisation.json`
```json
{
  "digitiser": "who you are: a person's name, or the AI model and tool",
  "source": {"arxiv_id": "0905.4383", "version": "v?", "pdf_sha256": "...", "page": 0, "figure": "3"},
  "nature_version_checked": "not checked | looks the same | differs: how",
  "method": "one or two sentences; details go in notes.md",
  "tool": "name and version, e.g. WebPlotDigitizer 4.x, or the script you wrote",
  "render_dpi": null,
  "x_axis": {"scale": "log", "plotted_range": [0, 0],
             "calibration": [{"pixel": [0, 0], "value": 0}, {"pixel": [0, 0], "value": 0}]},
  "y_axis": {"scale": "linear", "plotted_range": [0, 0],
             "calibration": [{"pixel": [0, 0], "value": 0}, {"pixel": [0, 0], "value": 0}]},
  "y_axis_label": "as printed",
  "error_bars_stated_as": "what the paper says the error bars are, paraphrased, or 'not stated'",
  "other_marks_in_figure": "lines, curves, insets or labels other than the data points",
  "started_utc": "YYYY-MM-DDTHH:MMZ",
  "finished_utc": "YYYY-MM-DDTHH:MMZ",
  "had_seen_retrace_result": false,
  "had_seen_other_digitisation": false
}
```
`plotted_range` is the range of the axis as drawn (from one end of the axis to the other). Use at least two
labelled tick marks per axis for calibration, as far apart as possible. For a vector extraction, give the
coordinates in the PDF's own units as `pixel`. `render_dpi` is `null` for a vector extraction.

### `notes.md`
What you did, step by step, and any problems or doubts. AI agents also list every file they opened and every
URL they fetched, and quote their prompt word for word. If you used WebPlotDigitizer, you may add its project
data as `wpd.json` (take it out of the `.tar` project; never commit the `.tar`, which contains the image).

## Committing
Commit your folder in a single commit on a branch named `digitise/<id>`. Don't push and don't open GitHub
issues or pull requests: the maintainer does that.

## Prompt for an AI digitiser
Drafted by the explainer. The maintainer fills in the two placeholders, starts the agent in a new empty folder, and
pastes this prompt unchanged. The agent quotes it in its `notes.md`.

> You are a digitiser for the Retrace project (https://github.com/phajy/Retrace). Your job is to read the data
> points off one published figure as accurately as you can, and to record exactly how you did it. You are not
> comparing anything.
>
> 1. In this empty folder, clone the repository and check out commit `<COMMIT>` on a new branch:
>    `git clone https://github.com/phajy/Retrace.git . && git checkout -b digitise/<ID> <COMMIT>`
> 2. Read `results/compare/DIGITISE.md` and `results/compare/PLAN.md`, then follow `DIGITISE.md`. Do not open any
>    other file in the repository, and do not look at other branches or commits. In particular, do not open
>    `README.md` or anything under `analysis/`, `docs/`, `verification/` or elsewhere in `results/`. They contain
>    the project's own result, and your reading of the figure must not be influenced by it.
> 3. Write your output to `results/compare/digitised/<ID>/` as `DIGITISE.md` describes, and commit it on your
>    branch. Do not push, and do not open GitHub issues or pull requests.
> 4. When you finish, report what you did plainly, including anything you could not do or were unsure about.
>    If you cannot see a value clearly, leave it empty and say so; don't guess.

# Prompt for a verifier

**Status: reviewed.** Drafted by the explainer (Claude Opus 5.5 in Claude Code) on 2026-11-20, and reviewed by the
maintainer on the same day without changes to the prompt text. The commit that added this file holds the reviewed
version. Any later change to the prompt is reviewed again and recorded in `docs/LOG.md`.

## Why one prompt for every check
Whoever writes a verifier's instructions can steer it ([Independence and its limits](../docs/METHODOLOGY.md#independence-and-its-limits)).
The first verifier's prompt was drafted by the explainer for that one check. From now on, every verifier gets
the same prompt, below, for every result and every check type. Only the three fields at the top are filled in.
So no one writes instructions for a particular check, and the prompt says nothing about any result, any expected
outcome or any known concern.

The prompt does not say whether the commit contains mistakes. Planted-mistake tests use the same prompt.

## How to use it
1. Start the verifier in a **new empty folder** and a **new workspace or session** with no earlier history of this
   project. Prefer a model family different from the explainer's ([METHODOLOGY](../docs/METHODOLOGY.md#independence-and-its-limits)).
2. Fill in the three fields: the commit, the tasks and the verifier's model and tool. Change nothing else.
3. Paste the prompt. The verifier quotes it in its report.
4. During the run, answer only practical questions (permissions, downloads), not questions about the method.
   The verifier records every exchange.

Example tasks:
* `R1 and R3: re-run.`
* `R1 and R3: re-derived, starting from the raw archive files.`
* `R1 compared with the paper: compared, with your own code written from results/compare/PLAN.md.`
* `R1 compared with the paper: compared, by re-running the compare stage.`

## The prompt
```text
You are an independent verifier for Retrace, a public proof of concept for checking published science:
https://github.com/phajy/Retrace
You are not the explainer (the agent that did the analysis), and you have not seen its conversations. The
commit you check may contain mistakes, in the code or in the written record. Finding them is the point of
your work. "This did not reproduce" and "these instructions did not work" are useful results.

Commit: <COMMIT>
Tasks (one per line: result, check, and how):
<TASKS>
Your model and tool: <MODEL AND TOOL>

Always do SET-UP and REPORT. Of RE-RUN, RE-DERIVED and COMPARED, do the sections your tasks name.

SET-UP
1. In this empty folder, clone the repository and check out the commit on a new branch:
     git clone https://github.com/phajy/Retrace.git . && git checkout -b verification/<date>-<you> <COMMIT>
   <date> is today's date (YYYY-MM-DD) and <you> is a short name for your model. Record the start time
   (UTC). Do not use files from any other copy of the project, from other branches or from later commits.
2. Read docs/METHODOLOGY.md, verification/README.md and the honesty rules in CLAUDE.md. CLAUDE.md is
   written for the explainer: follow its honesty rules, and where it differs from this prompt, follow this
   prompt. The check types (re-run, re-derived, compared) are defined in docs/METHODOLOGY.md.
3. From now on, keep a reading log: every file you open, when (UTC) and why.
4. Do not ask the maintainer about the method. The maintainer may know things that are not in the written
   record (in this pilot, the maintainer is a co-author of the paper being reproduced). Where the record
   leaves a choice open, make your own choice, record it as your assumption and carry on. Ask only about
   practical blockers, such as permissions or downloads.

RE-RUN
5. Follow README.md, "Reproduce it yourself", exactly, in a new .venv inside the clone. If a step fails,
   record the command and its output, make the smallest workaround you can and record that too. Compare
   your outputs with the committed ones as verification/README.md describes. Report every difference,
   however small, with numbers. Never change pipeline code or parameters to make things match.

RE-DERIVED (two phases, in this order)
6. Phase 1, derive. From dvc.yaml, find the pipeline stages the result depends on, from the starting point
   the task names. Until you have committed phase 1 (step 7):
   * Read only the method: README.md (only the sections "How it works", "Pipeline", "Reproduce it
     yourself" and "Repository map"), the analysis specification in docs/, docs/assumptions.md,
     params.yaml, dvc.yaml, and each of these stages' EXPLAIN.md, skipping sections headed "Results" or
     "Comparison".
   * Do not open the explainer's code for these stages, their committed outputs (summary.json,
     content_hashes.json, tables, figures, the checksums in dvc.lock), docs/LOG.md, or anything under
     results/ or verification/ other than verification/README.md and verification/PROMPT.md.
   * Do not run the explainer's pipeline (dvc repro). You may download the inputs it names (for example
     dvc update -R reduction/raw).
   * Write your own code from the method. Any general library is fine; say which you used.
   You may still see some of the explainer's numbers in what you are allowed to read. Never adjust
   anything to move towards them.
7. Before comparing anything, write down what you will count as a match. For example: differences small
   compared with the error bars, since the data are the same; the same bins flagged as reliable. Then commit
   your code, your outputs and this criterion. The commit records that phase 1 came first.
8. Phase 2, compare. Now you may read everything, including the explainer's code and outputs, and run its
   pipeline. Compare value by value, and judge against the criterion you committed.
   * Where you differ, find out why if you can, and say whether the cause is in your code, in the
     explainer's code, or in the written record (unclear, incomplete, or not what the code does).
   * If you change your own code after the first comparison, commit the new version, report both
     versions, and base the outcome on the first.
   * Do not edit the explainer's files. If you think they contain a mistake, show its effect with a
     changed copy in your own folder, clearly labelled.

COMPARED
9. A comparison with the publication follows the written plan that the task names. Either re-run the
   comparison's DVC stage and compare its outputs with the committed ones, or write your own comparison
   code from the plan before reading the explainer's comparison code, and see whether it gives the same
   numbers and the same outcome. The task says which. If you also re-derive the result in this session,
   finish phase 1 of the re-derivation first.

REPORT
10. Write verification/<date>-<you>/REPORT.md in the format that verification/README.md gives. Also include:
    * the reading log;
    * every assumption you made;
    * every place where the written record was unclear or wrong, or did not match the code;
    * the start and end times, any messages from humans during the work, and tokens or cost if your tool
      shows them;
    * this prompt, word for word.
    Put your code, small outputs (under 1 MB each) and logs in the same folder. Never commit raw data or
    FITS files.
11. Commit on your branch. Do not push, open issues or open pull requests. Stop and show the report.
```

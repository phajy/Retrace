#!/bin/sh
# Creates (or updates) the issue labels described in docs/METHODOLOGY.md.
# Needs the GitHub CLI (`gh`), authenticated with write access to the repository.
set -e
label() { gh label create "$1" --color "$2" --description "$3" --force; }
label "check-request"          d93f0b "A specific, runnable test of a result"
label "question"               d876e3 "A request for explanation"
label "verification"           0e8a16 "Report of an independent re-run, re-derivation or comparison"
label "outcome: confirmed"     c2e0c6 "The check ran and the result stands"
label "outcome: changed"       fbca04 "The check ran and the result changed (stated, non-tuning reason)"
label "outcome: mistake found" b60205 "The check found an error"
label "outcome: inconclusive"  cfd3d7 "The check could not settle the question"
label "planted-mistake-test"   5319e7 "Deliberate, labelled error used to test the checks"
